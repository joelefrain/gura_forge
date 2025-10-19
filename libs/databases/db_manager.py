import os
import random
import shutil
import string
import sqlite3

from abc import ABC
from datetime import datetime

from libs.helpers.storage_helpers import validate_folder, validate_file
from libs.config.config_variables import (
    DATABASE_PATH,
    STORAGE_DIR,
    ALLOWABLE_INSTRUMENTS_TYPES,
)

from libs.config.config_logger import get_logger

logger = get_logger()


class FileSystemManager:
    @staticmethod
    def create_folder(path):
        """Crea una carpeta si no existe"""
        if path and not os.path.exists(path):
            validate_folder(path, create_if_missing=True)
            logger.info(f"Carpeta creada: {path}")
            return True
        return False

    @staticmethod
    def rename_folder(old_path, new_path):
        """Renombra una carpeta"""
        if (
            old_path
            and new_path
            and os.path.exists(old_path)
            and not os.path.exists(new_path)
        ):
            # Crear directorio padre si no existe
            parent_dir = os.path.dirname(new_path)
            FileSystemManager.create_folder(parent_dir)

            try:
                os.rename(old_path, new_path)
                logger.info(f"Carpeta renombrada: {old_path} -> {new_path}")
                return True
            except OSError as e:
                logger.error(f"Error renombrando carpeta {old_path} -> {new_path}: {e}")
                return False
        return False

    @staticmethod
    def delete_folder(path):
        """Elimina una carpeta y todo su contenido"""
        if path and os.path.exists(path):
            try:
                shutil.rmtree(path)
                logger.info(f"Carpeta eliminada: {path}")
                return True
            except OSError as e:
                logger.error(f"Error eliminando carpeta {path}: {e}")
                return False
        return False

    @staticmethod
    def create_file(file_path, content=""):
        """Crea un archivo con contenido inicial"""
        if file_path and not os.path.exists(file_path):
            try:
                validate_file(file_path, create_parents=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"Archivo creado: {file_path}")
                return True
            except OSError as e:
                logger.error(f"Error creando archivo {file_path}: {e}")
                return False
        return False


class CodeDuplicationHandler:
    """Maneja la generación de códigos únicos cuando hay duplicaciones"""

    @staticmethod
    def generate_unique_code(base_code, check_function, max_attempts=100):
        """
        Genera un código único basado en un código base
        Args:
            base_code: El código base a usar
            check_function: Función que verifica si el código existe (debe retornar True si existe)
            max_attempts: Número máximo de intentos
        Returns:
            Un código único o None si no se pudo generar
        """
        if not check_function(base_code):
            return base_code

        # Intentar con sufijos numéricos
        for i in range(1, max_attempts + 1):
            candidate_code = f"{base_code}_{i:03d}"
            if not check_function(candidate_code):
                return candidate_code

        # Si no funciona con números, intentar con timestamp + random
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=4)
        )
        fallback_code = f"{base_code}_{timestamp}_{random_suffix}"

        if not check_function(fallback_code):
            return fallback_code

        logger.error(f"No se pudo generar código único para: {base_code}")
        return None


class BaseModel(ABC):
    """Clase base abstracta para todos los modelos"""

    TABLE_NAME = None
    COLUMNS = []
    UNIQUE_FIELDS = []  # Campos que deben ser únicos

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def save(self):
        """Guarda el objeto en la base de datos"""
        try:
            if hasattr(self, "id") and self.id:
                self._save_update()
            else:
                self._save_insert()

        except Exception as e:
            logger.error(f"Error guardando {self.__class__.__name__}: {e}")
            raise

    def _save_insert(self):
        """Maneja la lógica de inserción con manejo de duplicados"""
        # Verificar si ya existe por campos únicos
        existing = self._find_existing_by_unique_fields()
        if existing:
            # Omitir la inserción y registrar una advertencia
            unique_values = {
                field: getattr(self, field, None) for field in self.UNIQUE_FIELDS
            }
            logger.warning(
                f"Se omite la inserción en {self.__class__.__name__} debido a un registro duplicado en campos únicos: {unique_values}"
            )
            return

        # Manejar códigos duplicados antes de insertar
        if hasattr(self, "code") and self.code:
            try:
                self._ensure_unique_code()
            except ValueError as e:
                logger.error(f"Error al generar código único: {e}")
                return

        # Intentar la inserción y manejar errores de unicidad
        try:
            self.insert()
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint" in str(e):
                logger.warning(
                    f"Violación de unicidad al insertar {self.__class__.__name__}: {self.UNIQUE_FIELDS}"
                )
            else:
                # Get a suitable identifier for the error message
                identifier = (
                    getattr(self, "code", None)
                    or getattr(self, "session_code", None)
                    or "unknown"
                )
                logger.error(
                    f"Error de integridad al insertar {self.__class__.__name__} - '{identifier}': {e}"
                )
                raise

    def _save_update(self):
        """Maneja la lógica de actualización"""
        # Obtener estado anterior para comparación
        old_instance = self.get(self.id)

        # Manejar códigos duplicados antes de actualizar
        if hasattr(self, "code") and self.code and old_instance:
            if old_instance.code != self.code:
                self._ensure_unique_code(exclude_id=self.id)

        self.update(old_instance)

    def _ensure_unique_code(self, exclude_id=None):
        """Asegura que el código sea único, generando uno nuevo si es necesario"""
        if not hasattr(self, "code") or not self.code:
            return

        original_code = self.code

        def check_code_exists(code):
            return self._code_exists(code, exclude_id)

        unique_code = CodeDuplicationHandler.generate_unique_code(
            self.code, check_code_exists
        )

        if unique_code is None:
            raise ValueError(
                f"No se pudo generar un código único para: {original_code}"
            )

        if unique_code != original_code:
            logger.warning(
                f"Código duplicado detectado. Cambiando {original_code} -> {unique_code}"
            )
            self.code = unique_code
            # Actualizar rutas que dependen del código
            if hasattr(self, "_update_paths"):
                self._update_paths()

    def _find_existing_by_unique_fields(self):
        """Busca un registro existente basado en campos únicos"""
        if not self.UNIQUE_FIELDS:
            return None

        conn = self._get_connection()
        cursor = conn.cursor()

        conditions = []
        values = []

        for field in self.UNIQUE_FIELDS:
            if hasattr(self, field) and getattr(self, field) is not None:
                conditions.append(f"{field}=?")
                values.append(getattr(self, field))

        if not conditions:
            conn.close()
            return None

        where_clause = " AND ".join(conditions)
        query = f"SELECT * FROM {self.TABLE_NAME} WHERE {where_clause}"

        try:
            cursor.execute(query, values)
            row = cursor.fetchone()

            if row:
                return self._create_from_row(row)
            return None
        finally:
            conn.close()

    def insert(self):
        """Inserta un nuevo registro en la base de datos"""
        conn = self._get_connection()
        cursor = conn.cursor()

        data = self._prepare_data()
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        query = f"INSERT INTO {self.TABLE_NAME} ({columns}) VALUES ({placeholders})"

        try:
            cursor.execute(query, tuple(data.values()))
            self.id = cursor.lastrowid
            conn.commit()

            # Crear carpetas después de insertar exitosamente
            self.create_associated_folders()

        except sqlite3.IntegrityError as e:
            conn.rollback()
            logger.error(
                f"Error de integridad al insertar {self.__class__.__name__}: {e}"
            )
            raise
        finally:
            conn.close()

    def update(self, old_instance=None):
        """Actualiza un registro existente en la base de datos"""
        if not old_instance:
            old_instance = self.get(self.id) if hasattr(self, "id") else None

        conn = self._get_connection()
        cursor = conn.cursor()

        data = self._prepare_data()
        set_clause = ", ".join([f"{k}=?" for k in data.keys()])
        query = f"UPDATE {self.TABLE_NAME} SET {set_clause} WHERE id=?"

        values = tuple(data.values()) + (self.id,)

        try:
            cursor.execute(query, values)
            conn.commit()

            # Actualizar carpetas si es necesario
            if old_instance:
                self.rename_associated_folders(old_instance)

        except sqlite3.IntegrityError as e:
            conn.rollback()
            logger.error(
                f"Error de integridad al actualizar {self.__class__.__name__}: {e}"
            )
            raise
        finally:
            conn.close()

    def _code_exists(self, code, exclude_id=None):
        """Verifica si un código ya existe considerando los campos únicos"""
        conn = self._get_connection()
        cursor = conn.cursor()

        conditions = ["code=?"]
        values = [code]

        # Agregar otras condiciones basadas en UNIQUE_FIELDS
        for field in self.UNIQUE_FIELDS:
            if (
                field != "code"
                and hasattr(self, field)
                and getattr(self, field) is not None
            ):
                conditions.append(f"{field}=?")
                values.append(getattr(self, field))

        # Excluir el registro actual si estamos actualizando
        if exclude_id:
            conditions.append("id!=?")
            values.append(exclude_id)

        where_clause = " AND ".join(conditions)
        query = f"SELECT id FROM {self.TABLE_NAME} WHERE {where_clause}"

        try:
            cursor.execute(query, values)
            result = cursor.fetchone()
            return result is not None
        finally:
            conn.close()

    def _prepare_data(self):
        """Prepara los datos para inserción/actualización"""
        return {
            k: v
            for k, v in self.__dict__.items()
            if k in self.COLUMNS and k != "id" and not callable(v)
        }

    def _get_connection(self):
        """Obtiene una conexión a la base de datos"""
        return sqlite3.connect(DATABASE_PATH)

    def delete(self):
        """Elimina el registro de la base de datos"""
        if not hasattr(self, "id") or not self.id:
            return

        # Eliminar carpetas primero
        self.delete_associated_folders()

        conn = self._get_connection()
        cursor = conn.cursor()
        query = f"DELETE FROM {self.TABLE_NAME} WHERE id=?"
        cursor.execute(query, (self.id,))
        conn.commit()
        conn.close()

    @classmethod
    def get(cls, id):
        """Obtiene un registro por ID"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE id=?"
        cursor.execute(query, (id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return cls(**dict(zip(cls.COLUMNS, row)))
        return None

    @classmethod
    def get_by_code(cls, code):
        """Obtiene un registro por código"""
        results = cls.get_by_field("code", code)
        return results[0] if results else None

    @classmethod
    def _create_from_row(cls, row):
        """Crea una instancia a partir de una fila de la base de datos"""
        return cls(**dict(zip(cls.COLUMNS, row)))

    @classmethod
    def get_all(cls):
        """Obtiene todos los registros de la tabla"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        query = f"SELECT * FROM {cls.TABLE_NAME}"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return [cls._create_from_row(row) for row in rows]

    @classmethod
    def get_by_field(cls, field, value):
        """Obtiene registros por un campo específico"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE {field}=?"
        cursor.execute(query, (value,))
        rows = cursor.fetchall()
        conn.close()

        return [cls._create_from_row(row) for row in rows]

    def create_associated_folders(self):
        """Crea carpetas asociadas a esta entidad (para implementar en subclases)"""
        pass

    def rename_associated_folders(self, old_instance):
        """Renombra carpetas asociadas si es necesario (para implementar en subclases)"""
        pass

    def delete_associated_folders(self):
        """Elimina carpetas asociadas a esta entidad (para implementar en subclases)"""
        pass


class TranslationKey(BaseModel):
    TABLE_NAME = "translation_key"
    COLUMNS = ["id", "key_name"]
    UNIQUE_FIELDS = ["key_name"]

    @classmethod
    def get_by_name(cls, key_name):
        """Obtiene una clave de traducción por nombre"""
        results = cls.get_by_field("key_name", key_name)
        return results[0] if results else None


class Translation(BaseModel):
    TABLE_NAME = "translation"
    COLUMNS = ["key_id", "language_code", "translated_text"]

    @classmethod
    def get_translations(cls, key_id):
        """Obtiene todas las traducciones para una clave"""
        return cls.get_by_field("key_id", key_id)

    @classmethod
    def delete_by_key_id(cls, key_id):
        """Elimina todas las traducciones para una clave específica"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        query = f"DELETE FROM {cls.TABLE_NAME} WHERE key_id=?"
        cursor.execute(query, (key_id,))
        conn.commit()
        conn.close()

    @classmethod
    def upsert(cls, key_id, language_code, translated_text):
        """Inserta o actualiza una traducción"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Intentar actualizar primero
        update_query = """
            UPDATE translation 
            SET translated_text = ? 
            WHERE key_id = ? AND language_code = ?
        """
        cursor.execute(update_query, (translated_text, key_id, language_code))

        # Si no se actualizó ninguna fila, insertar
        if cursor.rowcount == 0:
            insert_query = """
                INSERT INTO translation (key_id, language_code, translated_text) 
                VALUES (?, ?, ?)
            """
            cursor.execute(insert_query, (key_id, language_code, translated_text))

        conn.commit()
        conn.close()


class TranslatableModel(BaseModel, ABC):
    """Clase base para modelos con campos traducibles"""

    TRANSLATION_PREFIX = None

    def __init__(self, name_translations=None, **kwargs):
        super().__init__(**kwargs)
        self.name_translations = name_translations or {}

    def save(self):
        """Guarda el objeto y sus traducciones"""
        is_update = hasattr(self, "id") and self.id

        if is_update:
            if not hasattr(self, "name_key_id") or not self.name_key_id:
                self._create_translation_key()
            self._save_translations()
            super().save()
        else:
            if not hasattr(self, "name_key_id") or not self.name_key_id:
                self._create_translation_key()
            super().save()
            self._save_translations()

    def _create_translation_key(self):
        """Crea una nueva clave de traducción"""
        if not self.TRANSLATION_PREFIX:
            raise ValueError("TRANSLATION_PREFIX must be defined")

        base_key_name = f"{self.TRANSLATION_PREFIX}_{self.code}"

        def check_key_exists(key_name):
            return TranslationKey.get_by_name(key_name) is not None

        unique_key_name = CodeDuplicationHandler.generate_unique_code(
            base_key_name, check_key_exists
        )

        if unique_key_name is None:
            raise ValueError(
                f"No se pudo generar clave de traducción única para: {base_key_name}"
            )

        key = TranslationKey(key_name=unique_key_name)
        key.save()
        self.name_key_id = key.id

    def _save_translations(self):
        """Guarda las traducciones asociadas usando upsert"""
        if not hasattr(self, "name_key_id") or not self.name_key_id:
            return

        for lang, text in self.name_translations.items():
            if text:
                Translation.upsert(self.name_key_id, lang, text)

    def get_name(self, language_code="es"):
        """Obtiene el nombre traducido"""
        if not hasattr(self, "name_key_id") or not self.name_key_id:
            return None

        translations = Translation.get_by_field("key_id", self.name_key_id)
        for trans in translations:
            if trans.language_code == language_code:
                return trans.translated_text

        return translations[0].translated_text if translations else None

    def delete(self):
        """Elimina el objeto y sus traducciones"""
        if hasattr(self, "name_key_id") and self.name_key_id:
            Translation.delete_by_key_id(self.name_key_id)
            key = TranslationKey.get(self.name_key_id)
            if key:
                key.delete()

        super().delete()


class Client(TranslatableModel):
    TABLE_NAME = "client"
    COLUMNS = ["id", "name_key_id", "code", "logo_path"]
    TRANSLATION_PREFIX = "client"
    UNIQUE_FIELDS = ["code"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_paths()

    def _update_paths(self):
        """Actualiza las rutas basadas en el código actual"""
        if hasattr(self, "code") and self.code:
            self.logo_path = f"{STORAGE_DIR}/logos/{self.code}"

    def create_associated_folders(self):
        """Crea la carpeta para el logo"""
        FileSystemManager.create_folder(self.logo_path)

    def rename_associated_folders(self, old_instance):
        """Renombra todas las carpetas cuando el código cambia"""
        if not old_instance or old_instance.code == self.code:
            return

        # Renombrar carpeta de logo
        old_logo_path = old_instance.logo_path
        new_logo_path = self.logo_path
        FileSystemManager.rename_folder(old_logo_path, new_logo_path)

        # Renombrar todas las carpetas relacionadas de unidades mineras
        self._rename_mining_unit_folders(old_instance.code, self.code)

    def _rename_mining_unit_folders(self, old_code, new_code):
        """Renombra todas las carpetas de unidades mineras del cliente"""
        mining_units = self.get_mining_units()

        for unit in mining_units:
            # Actualizar rutas de geometrías
            old_geom_path = f"{STORAGE_DIR}/geometries/{old_code}/{unit.code}"
            new_geom_path = f"{STORAGE_DIR}/geometries/{new_code}/{unit.code}"
            FileSystemManager.rename_folder(old_geom_path, new_geom_path)

            # Actualizar rutas de documentación
            old_doc_path = f"{STORAGE_DIR}/documentation/{old_code}/{unit.code}"
            new_doc_path = f"{STORAGE_DIR}/documentation/{new_code}/{unit.code}"
            FileSystemManager.rename_folder(old_doc_path, new_doc_path)

            # Renombrar carpetas de estructuras mineras
            structures = unit.get_structures()
            for structure in structures:
                old_prep_path = f"{STORAGE_DIR}/config/preprocessor/{old_code}/{unit.code}/{structure.code}"
                new_prep_path = f"{STORAGE_DIR}/config/preprocessor/{new_code}/{unit.code}/{structure.code}"
                FileSystemManager.rename_folder(old_prep_path, new_prep_path)

            # Renombrar carpetas de proyectos
            projects = unit.get_projects()
            for project in projects:
                old_proj_path = (
                    f"{STORAGE_DIR}/config/postprocessor/{old_code}/{unit.code}"
                )
                new_proj_path = (
                    f"{STORAGE_DIR}/config/postprocessor/{new_code}/{unit.code}"
                )
                FileSystemManager.rename_folder(old_proj_path, new_proj_path)

                # Renombrar carpetas de sesiones
                sessions = project.get_sessions()
                for session in sessions:
                    session_paths = [
                        (
                            f"{STORAGE_DIR}/temp/{old_code}/{unit.code}/{session.get_code()}",
                            f"{STORAGE_DIR}/temp/{new_code}/{unit.code}/{session.get_code()}",
                        ),
                        (
                            f"{STORAGE_DIR}/outputs/{old_code}/{unit.code}/{session.get_code()}",
                            f"{STORAGE_DIR}/outputs/{new_code}/{unit.code}/{session.get_code()}",
                        ),
                        (
                            f"{STORAGE_DIR}/raw_data/{old_code}/{unit.code}/{session.get_code()}",
                            f"{STORAGE_DIR}/raw_data/{new_code}/{unit.code}/{session.get_code()}",
                        ),
                    ]

                    for old_path, new_path in session_paths:
                        FileSystemManager.rename_folder(old_path, new_path)

    def delete_associated_folders(self):
        """Elimina la carpeta del logo"""
        FileSystemManager.delete_folder(self.logo_path)

    def get_mining_units(self):
        """Obtiene todas las unidades mineras del cliente"""
        return (
            MiningUnit.get_by_field("client_id", self.id) if hasattr(self, "id") else []
        )

    @classmethod
    def get_units_by_code(cls, client_code):
        """Obtiene todos los códigos de unidades mineras de un cliente"""
        client = cls.get_by_code(client_code)
        if not client:
            return []
        units = client.get_mining_units()
        return [unit.code for unit in units] if units else []


class MiningUnit(TranslatableModel):
    TABLE_NAME = "mining_unit"
    COLUMNS = [
        "id",
        "client_id",
        "name_key_id",
        "code",
        "geometries_path",
        "documentation_path",
        "utm_zone",
    ]
    TRANSLATION_PREFIX = "mining_unit"
    UNIQUE_FIELDS = ["client_id", "code"]

    def __init__(self, client_code=None, **kwargs):
        # Resolver client_id a partir de client_code si se proporciona
        if client_code and "client_id" not in kwargs:
            client = Client.get_by_code(client_code)
            if not client:
                raise ValueError(f"Cliente con código '{client_code}' no encontrado")
            kwargs["client_id"] = client.id

        super().__init__(**kwargs)
        self._update_paths()

    def _update_paths(self):
        """Actualiza las rutas basadas en el cliente y código actual"""
        client = self.get_client()
        if client and hasattr(self, "code") and self.code:
            self.geometries_path = f"{STORAGE_DIR}/geometries/{client.code}/{self.code}"
            self.documentation_path = (
                f"{STORAGE_DIR}/documentation/{client.code}/{self.code}"
            )

    def get_client(self):
        """Obtiene el cliente asociado a esta unidad minera"""
        return (
            Client.get(self.client_id)
            if hasattr(self, "client_id") and self.client_id
            else None
        )

    def create_associated_folders(self):
        """Crea las carpetas de geometrías y documentación"""
        FileSystemManager.create_folder(self.geometries_path)
        FileSystemManager.create_folder(self.documentation_path)

        # Crear subcarpetas de geometrías
        subfolders = ["polylines", "surfaces", "sections", "ortophotos"]
        for folder in subfolders:
            path = os.path.join(self.geometries_path, folder)
            FileSystemManager.create_folder(path)

    def rename_associated_folders(self, old_instance):
        """Renombra todas las carpetas cuando el código o cliente cambia"""
        if not old_instance or (
            old_instance.code == self.code and old_instance.client_id == self.client_id
        ):
            return

        # Renombrar carpetas principales
        FileSystemManager.rename_folder(
            old_instance.geometries_path, self.geometries_path
        )
        FileSystemManager.rename_folder(
            old_instance.documentation_path, self.documentation_path
        )

        # Renombrar carpetas de estructuras
        structures = self.get_structures()
        old_client = Client.get(old_instance.client_id)
        new_client = self.get_client()

        if old_client and new_client:
            for structure in structures:
                old_prep_path = f"{STORAGE_DIR}/config/preprocessor/{old_client.code}/{old_instance.code}/{structure.code}"
                new_prep_path = f"{STORAGE_DIR}/config/preprocessor/{new_client.code}/{self.code}/{structure.code}"
                FileSystemManager.rename_folder(old_prep_path, new_prep_path)

        # Renombrar carpetas de proyectos y sesiones
        projects = self.get_projects()
        for project in projects:
            if old_client and new_client:
                old_proj_path = f"{STORAGE_DIR}/config/postprocessor/{old_client.code}/{old_instance.code}"
                new_proj_path = (
                    f"{STORAGE_DIR}/config/postprocessor/{new_client.code}/{self.code}"
                )
                FileSystemManager.rename_folder(old_proj_path, new_proj_path)

                # Renombrar carpetas de sesiones
                sessions = project.get_sessions()
                for session in sessions:
                    session_paths = [
                        (
                            f"{STORAGE_DIR}/temp/{old_client.code}/{old_instance.code}/{session.get_code()}",
                            f"{STORAGE_DIR}/temp/{new_client.code}/{self.code}/{session.get_code()}",
                        ),
                        (
                            f"{STORAGE_DIR}/outputs/{old_client.code}/{old_instance.code}/{session.get_code()}",
                            f"{STORAGE_DIR}/outputs/{new_client.code}/{self.code}/{session.get_code()}",
                        ),
                        (
                            f"{STORAGE_DIR}/raw_data/{old_client.code}/{old_instance.code}/{session.get_code()}",
                            f"{STORAGE_DIR}/raw_data/{new_client.code}/{self.code}/{session.get_code()}",
                        ),
                    ]

                    for old_path, new_path in session_paths:
                        FileSystemManager.rename_folder(old_path, new_path)

    def delete_associated_folders(self):
        """Elimina las carpetas de geometrías y documentación"""
        FileSystemManager.delete_folder(self.geometries_path)
        FileSystemManager.delete_folder(self.documentation_path)

    def get_structures(self):
        """Obtiene todas las estructuras de esta unidad minera"""
        return (
            MineStructure.get_by_field("mining_unit_id", self.id)
            if hasattr(self, "id")
            else []
        )

    def get_projects(self):
        """Obtiene todos los proyectos asociados a esta unidad minera"""
        return (
            EngineeringProject.get_by_field("mining_unit_id", self.id)
            if hasattr(self, "id")
            else []
        )

    @classmethod
    def get_unit_by_client_code(cls, client_code, unit_code):
        """Obtiene una unidad minera por código de cliente y código de unidad"""
        client = Client.get_by_code(client_code)
        if not client:
            return None

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE client_id=? AND code=?"
        cursor.execute(query, (client.id, unit_code))
        row = cursor.fetchone()
        conn.close()

        if row:
            return cls._create_from_row(row)
        return None

    @classmethod
    def get_structures_by_code(cls, client_code, unit_code):
        """Obtiene todos los códigos de estructuras de una unidad minera"""
        unit = cls.get_unit_by_client_code(client_code, unit_code)
        if not unit:
            return []
        structures = unit.get_structures()
        return [structure.code for structure in structures] if structures else []


class MineStructure(TranslatableModel):
    TABLE_NAME = "mine_structure"
    COLUMNS = [
        "id",
        "mining_unit_id",
        "name_key_id",
        "code",
        "min_east",
        "max_east",
        "min_north",
        "max_north",
        "preprocessor_path",
    ]
    TRANSLATION_PREFIX = "mine_structure"
    UNIQUE_FIELDS = ["mining_unit_id", "code"]

    def __init__(self, client_code=None, mining_unit_code=None, **kwargs):
        # Resolver mining_unit_id a partir de códigos si se proporcionan
        if client_code and mining_unit_code and "mining_unit_id" not in kwargs:
            mining_unit = MiningUnit.get_unit_by_client_code(
                client_code, mining_unit_code
            )
            if not mining_unit:
                raise ValueError(
                    f"Unidad minera con código '{mining_unit_code}' del cliente '{client_code}' no encontrada"
                )
            kwargs["mining_unit_id"] = mining_unit.id

        super().__init__(**kwargs)
        self._update_paths()

    def _update_paths(self):
        """Actualiza las rutas basadas en la estructura actual"""
        mining_unit = self.get_mining_unit()
        if mining_unit and hasattr(self, "code") and self.code:
            client = mining_unit.get_client()
            if client:
                self.preprocessor_path = (
                    f"{STORAGE_DIR}/config/preprocessor/{client.code}/"
                    f"{mining_unit.code}/{self.code}"
                )

    def get_mining_unit(self):
        """Obtiene la unidad minera asociada a esta estructura"""
        return (
            MiningUnit.get(self.mining_unit_id)
            if hasattr(self, "mining_unit_id") and self.mining_unit_id
            else None
        )

    def create_associated_folders(self):
        """Crea la carpeta de preprocesador"""
        FileSystemManager.create_folder(self.preprocessor_path)

        # Crear subcarpetas para cada tipo de instrumento
        instrument_types = ALLOWABLE_INSTRUMENTS_TYPES
        for inst_type in instrument_types:
            path = os.path.join(self.preprocessor_path, inst_type)
            FileSystemManager.create_folder(path)

            # Crear archivos de configuración
            folder_config = os.path.join(path, "folder_config.toml")
            parser_config = os.path.join(path, "parser_config.toml")
            FileSystemManager.create_file(folder_config, "# Configuración de carpeta")
            FileSystemManager.create_file(parser_config, "# Configuración de parser")

    def rename_associated_folders(self, old_instance):
        """Renombra la carpeta si el código, unidad minera o cliente cambiaron"""
        if not old_instance:
            return

        old_mining_unit = MiningUnit.get(old_instance.mining_unit_id)
        new_mining_unit = self.get_mining_unit()

        if old_mining_unit and new_mining_unit:
            # Verificar si cambió algo que afecte las rutas
            old_client = old_mining_unit.get_client()
            new_client = new_mining_unit.get_client()

            if (
                old_instance.code != self.code
                or old_instance.mining_unit_id != self.mining_unit_id
                or (old_client and new_client and old_client.code != new_client.code)
            ):
                FileSystemManager.rename_folder(
                    old_instance.preprocessor_path, self.preprocessor_path
                )

    def delete_associated_folders(self):
        """Elimina la carpeta de preprocesador"""
        FileSystemManager.delete_folder(self.preprocessor_path)

    def get_instruments(self):
        """Obtiene todos los instrumentos de esta estructura minera"""
        return (
            Instrument.get_by_field("mine_structure_id", self.id)
            if hasattr(self, "id")
            else []
        )

    def get_instruments_by_type(self, instrument_type_code):
        """Obtiene instrumentos filtrados por tipo"""
        instruments = self.get_instruments()
        return [
            inst
            for inst in instruments
            if inst.get_instrument_type()
            and inst.get_instrument_type().code == instrument_type_code
        ]

    @classmethod
    def get_by_client_unit_and_code(cls, client_code, unit_code, structure_code):
        """Obtiene una estructura por códigos de cliente, unidad y estructura"""
        mining_unit = MiningUnit.get_unit_by_client_code(client_code, unit_code)
        if not mining_unit:
            return None

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE mining_unit_id=? AND code=?"
        cursor.execute(query, (mining_unit.id, structure_code))
        row = cursor.fetchone()
        conn.close()

        if row:
            return cls._create_from_row(row)
        return None

    @classmethod
    def get_instruments_by_code(cls, client_code, unit_code, structure_code):
        """Obtiene los códigos de instrumentos agrupados por tipo"""
        structure = cls.get_by_client_unit_and_code(
            client_code, unit_code, structure_code
        )
        if not structure:
            return {}

        instruments = structure.get_instruments()
        if not instruments:
            return {}

        # Agrupar instrumentos por tipo
        instruments_by_type = {}
        for inst in instruments:
            inst_type = inst.get_instrument_type()
            if inst_type:
                type_code = inst_type.code
                if type_code not in instruments_by_type:
                    instruments_by_type[type_code] = []
                instruments_by_type[type_code].append(inst.code)

        return instruments_by_type


class EngineeringProject(TranslatableModel):
    TABLE_NAME = "engineering_project"
    COLUMNS = ["id", "mining_unit_id", "name_key_id", "code", "postprocessor_path"]
    TRANSLATION_PREFIX = "project"
    UNIQUE_FIELDS = ["mining_unit_id", "code"]

    def __init__(self, client_code=None, mining_unit_code=None, **kwargs):
        # Resolver mining_unit_id a partir de códigos si se proporcionan
        if client_code and mining_unit_code and "mining_unit_id" not in kwargs:
            mining_unit = MiningUnit.get_unit_by_client_code(
                client_code, mining_unit_code
            )
            if not mining_unit:
                raise ValueError(
                    f"Unidad minera con código '{mining_unit_code}' del cliente '{client_code}' no encontrada"
                )
            kwargs["mining_unit_id"] = mining_unit.id

        super().__init__(**kwargs)
        self._update_paths()

    def _update_paths(self):
        """Actualiza las rutas basadas en el proyecto actual"""
        mining_unit = self.get_mining_unit()
        if mining_unit and hasattr(self, "code") and self.code:
            client = mining_unit.get_client()
            if client:
                self.postprocessor_path = f"{STORAGE_DIR}/config/postprocessor/{client.code}/{mining_unit.code}/{self.code}"

    def get_mining_unit(self):
        """Obtiene la unidad minera asociada a este proyecto"""
        return (
            MiningUnit.get(self.mining_unit_id)
            if hasattr(self, "mining_unit_id") and self.mining_unit_id
            else None
        )

    def create_associated_folders(self):
        """Crea la carpeta de postprocesador"""
        FileSystemManager.create_folder(self.postprocessor_path)

    def rename_associated_folders(self, old_instance):
        """Renombra todas las carpetas cuando el código, unidad minera o cliente cambiaron"""
        if not old_instance:
            return

        old_mining_unit = MiningUnit.get(old_instance.mining_unit_id)
        new_mining_unit = self.get_mining_unit()

        if old_mining_unit and new_mining_unit:
            old_client = old_mining_unit.get_client()
            new_client = new_mining_unit.get_client()

            # Verificar si cambió algo que afecte las rutas
            if (
                old_instance.code != self.code
                or old_instance.mining_unit_id != self.mining_unit_id
                or (old_client and new_client and old_client.code != new_client.code)
            ):
                FileSystemManager.rename_folder(
                    old_instance.postprocessor_path, self.postprocessor_path
                )

                # Renombrar carpetas de sesiones
                sessions = self.get_sessions()
                for session in sessions:
                    if old_client and new_client:
                        session_paths = [
                            (
                                f"{STORAGE_DIR}/temp/{old_client.code}/{old_mining_unit.code}/{session.get_code()}",
                                f"{STORAGE_DIR}/temp/{new_client.code}/{new_mining_unit.code}/{session.get_code()}",
                            ),
                            (
                                f"{STORAGE_DIR}/outputs/{old_client.code}/{old_mining_unit.code}/{session.get_code()}",
                                f"{STORAGE_DIR}/outputs/{new_client.code}/{new_mining_unit.code}/{session.get_code()}",
                            ),
                            (
                                f"{STORAGE_DIR}/raw_data/{old_client.code}/{old_mining_unit.code}/{session.get_code()}",
                                f"{STORAGE_DIR}/raw_data/{new_client.code}/{new_mining_unit.code}/{session.get_code()}",
                            ),
                        ]

                        for old_path, new_path in session_paths:
                            FileSystemManager.rename_folder(old_path, new_path)

    def delete_associated_folders(self):
        """Elimina la carpeta de postprocesador"""
        FileSystemManager.delete_folder(self.postprocessor_path)

    def get_sessions(self):
        """Obtiene todas las sesiones de este proyecto"""
        return (
            Session.get_by_field("project_id", self.id) if hasattr(self, "id") else []
        )

    @classmethod
    def get_by_codes(cls, client_code, unit_code, project_code):
        """Obtiene un proyecto por códigos de cliente, unidad y proyecto"""
        mining_unit = MiningUnit.get_unit_by_client_code(client_code, unit_code)
        if not mining_unit:
            return None

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE mining_unit_id=? AND code=?"
        cursor.execute(query, (mining_unit.id, project_code))
        row = cursor.fetchone()
        conn.close()

        if row:
            return cls._create_from_row(row)
        return None


class Session(BaseModel):
    TABLE_NAME = "session"
    COLUMNS = [
        "id",
        "project_id",
        "session_code",
        "analysis_type",
        "session_name",
        "created_at",
        "raw_data_path",
        "temp_path",
        "outputs_path",
    ]
    UNIQUE_FIELDS = ["session_code"]

    def __init__(
        self,
        client_code=None,
        mining_unit_code=None,
        project_code=None,
        raw_data_path=None,
        temp_path=None,
        outputs_path=None,
        **kwargs,
    ):
        # Resolver project_id a partir de códigos si se proporcionan
        if (
            client_code
            and mining_unit_code
            and project_code
            and "project_id" not in kwargs
        ):
            project = EngineeringProject.get_by_codes(
                client_code, mining_unit_code, project_code
            )
            if not project:
                raise ValueError(f"Proyecto con código '{project_code}' no encontrado")
            kwargs["project_id"] = project.id

        super().__init__(**kwargs)

        # Inicializar session_code si no existe
        if not hasattr(self, "session_code") or not self.session_code:
            self.session_code = None

        # Actualizar rutas - usar los nombres correctos de los atributos de la DB
        if raw_data_path is not None:
            self.raw_data_path = raw_data_path
        elif not hasattr(self, "raw_data_path") or not self.raw_data_path:
            self.raw_data_path = self.get_raw_data_path()

        if temp_path is not None:
            self.temp_path = temp_path
        elif not hasattr(self, "temp_path") or not self.temp_path:
            self.temp_path = self.get_temp_path()

        if outputs_path is not None:
            self.outputs_path = outputs_path
        elif not hasattr(self, "outputs_path") or not self.outputs_path:
            self.outputs_path = self.get_outputs_path()

    def save(self):
        """Guarda la sesión generando automáticamente su código"""
        # Establecer fecha de creación si no existe
        if not hasattr(self, "created_at") or not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Generar código de sesión único si no existe
        if not self.session_code:
            self._generate_session_code()

        # Actualizar las rutas antes de guardar
        if not self.raw_data_path:
            self.raw_data_path = self.get_raw_data_path()
        if not self.temp_path:
            self.temp_path = self.get_temp_path()
        if not self.outputs_path:
            self.outputs_path = self.get_outputs_path()

        super().save()

    def _generate_session_code(self):
        """Genera un código único para la sesión"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_chars = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=8)
        )
        base_code = f"{timestamp}-{random_chars}"

        def check_session_exists(code):
            return len(Session.get_by_field("session_code", code)) > 0

        unique_code = CodeDuplicationHandler.generate_unique_code(
            base_code, check_session_exists
        )

        if unique_code is None:
            raise ValueError(
                f"No se pudo generar código de sesión único durante {timestamp}"
            )

        self.session_code = unique_code

        self.raw_data_path = self.get_raw_data_path()
        self.temp_path = self.get_temp_path()
        self.outputs_path = self.get_outputs_path()

    def get_code(self):
        """Obtiene el código de la sesión"""
        return self.session_code

    def get_name(self):
        """Alias para get_code() por compatibilidad"""
        return self.get_code()

    def get_temp_path(self):
        """Genera la ruta temporal para esta sesión"""
        project = self.get_project()
        if not project:
            return None

        mining_unit = project.get_mining_unit()
        if not mining_unit:
            return None

        client = mining_unit.get_client()
        if not client:
            return None

        return f"{STORAGE_DIR}/temp/{client.code}/{mining_unit.code}/{self.get_code()}"

    def get_outputs_path(self):
        """Genera la ruta de salida para esta sesión"""
        project = self.get_project()
        if not project:
            return None

        mining_unit = project.get_mining_unit()
        if not mining_unit:
            return None

        client = mining_unit.get_client()
        if not client:
            return None

        return (
            f"{STORAGE_DIR}/outputs/{client.code}/{mining_unit.code}/{self.get_code()}"
        )

    def get_raw_data_path(self):
        """Genera la ruta de datos crudos para esta sesión"""
        project = self.get_project()
        if not project:
            return None

        mining_unit = project.get_mining_unit()
        if not mining_unit:
            return None

        client = mining_unit.get_client()
        if not client:
            return None

        return (
            f"{STORAGE_DIR}/raw_data/{client.code}/{mining_unit.code}/{self.get_code()}"
        )

    def get_project(self):
        """Obtiene el proyecto asociado a esta sesión"""
        return (
            EngineeringProject.get(self.project_id)
            if hasattr(self, "project_id") and self.project_id
            else None
        )

    def create_associated_folders(self):
        """Crea todas las carpetas asociadas a esta sesión"""
        paths = [
            self.temp_path,  # Usar atributos directamente
            self.outputs_path,
            self.raw_data_path,
        ]
        for path in paths:
            if path:
                FileSystemManager.create_folder(path)

    def delete_associated_folders(self):
        """Elimina todas las carpetas asociadas a esta sesión"""
        paths = [
            self.temp_path,  # Usar atributos directamente
            self.outputs_path,
            self.raw_data_path,
        ]
        for path in paths:
            if path:
                FileSystemManager.delete_folder(path)


class InstrumentType(TranslatableModel):
    TABLE_NAME = "instrument_type"
    COLUMNS = ["id", "name_key_id", "code", "processor_path", "styles"]
    TRANSLATION_PREFIX = "instrument_type"
    UNIQUE_FIELDS = ["code"]

    @classmethod
    def get_by_code(cls, code):
        """Obtiene un tipo de instrumento por código"""
        results = cls.get_by_field("code", code)
        return results[0] if results else None


class Instrument(BaseModel):
    TABLE_NAME = "instrument"
    COLUMNS = [
        "id",
        "mine_structure_id",
        "instrument_type_id",
        "code",
        "east",
        "north",
        "vertical",
        "zone",
        "material",
        "metadata_instrument",
    ]
    UNIQUE_FIELDS = ["mine_structure_id", "code"]

    def __init__(
        self,
        client_code=None,
        mining_unit_code=None,
        structure_code=None,
        instrument_type_code=None,
        **kwargs,
    ):
        # Resolver IDs a partir de códigos
        if (
            client_code
            and mining_unit_code
            and structure_code
            and "mine_structure_id" not in kwargs
        ):
            structure = MineStructure.get_by_client_unit_and_code(
                client_code, mining_unit_code, structure_code
            )
            if not structure:
                raise ValueError(
                    f"Estructura '{structure_code}' en unidad '{mining_unit_code}' "
                    f"del cliente '{client_code}' no encontrada"
                )
            kwargs["mine_structure_id"] = structure.id

        if instrument_type_code and "instrument_type_id" not in kwargs:
            instrument_type = InstrumentType.get_by_code(instrument_type_code)
            if not instrument_type:
                raise ValueError(
                    f"Tipo de instrumento '{instrument_type_code}' no encontrado"
                )
            kwargs["instrument_type_id"] = instrument_type.id

        super().__init__(**kwargs)

    def get_structure(self):
        """Obtiene la estructura minera asociada"""
        return (
            MineStructure.get(self.mine_structure_id)
            if hasattr(self, "mine_structure_id") and self.mine_structure_id
            else None
        )

    def get_instrument_type(self):
        """Obtiene el tipo de instrumento"""
        return (
            InstrumentType.get(self.instrument_type_id)
            if hasattr(self, "instrument_type_id") and self.instrument_type_id
            else None
        )

    def get_alert_levels(self):
        """Obtiene todos los niveles de alerta para este instrumento"""
        return (
            AlertLevel.get_by_field("instrument_id", self.id)
            if hasattr(self, "id")
            else []
        )

    @classmethod
    def get_by_codes(
        cls,
        client_code,
        mining_unit_code,
        structure_code,
        instrument_code,
    ):
        """Obtiene un instrumento por códigos completos"""
        structure = MineStructure.get_by_client_unit_and_code(
            client_code, mining_unit_code, structure_code
        )
        if not structure:
            return None

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE mine_structure_id=? AND code=?"
        cursor.execute(query, (structure.id, instrument_code))
        row = cursor.fetchone()
        conn.close()

        if row:
            return cls._create_from_row(row)
        return None


class AlertLevel(TranslatableModel):
    TABLE_NAME = "alert_level"
    COLUMNS = [
        "id",
        "instrument_id",
        "name_key_id",
        "code",
        "calc_column",
        "measure",
        "color",
    ]
    TRANSLATION_PREFIX = "alert_level"
    UNIQUE_FIELDS = ["instrument_id", "code"]

    def __init__(
        self,
        client_code=None,
        mining_unit_code=None,
        structure_code=None,
        instrument_code=None,
        **kwargs,
    ):
        # Resolver instrument_id a partir de códigos
        if (
            client_code
            and mining_unit_code
            and structure_code
            and instrument_code
            and "instrument_id" not in kwargs
        ):
            instrument = Instrument.get_by_codes(
                client_code, mining_unit_code, structure_code, instrument_code
            )
            if not instrument:
                raise ValueError(
                    f"Instrumento '{instrument_code}' en estructura '{structure_code}' "
                    f"de unidad '{mining_unit_code}' del cliente '{client_code}' no encontrado"
                )
            kwargs["instrument_id"] = instrument.id

        super().__init__(**kwargs)

    def get_instrument(self):
        """Obtiene el instrumento asociado"""
        return (
            Instrument.get(self.instrument_id)
            if hasattr(self, "instrument_id") and self.instrument_id
            else None
        )


class InstrumentDataModel(BaseModel):
    """Clase base para modelos de datos de instrumentos"""

    PRIMARY_KEYS = ["instrument_id", "time", "session_id"]

    def save(self):
        """Implementación específica para tablas sin ROWID"""
        try:
            if all(
                hasattr(self, key) and getattr(self, key) is not None
                for key in self.PRIMARY_KEYS
            ):
                primary_key_values = [getattr(self, key) for key in self.PRIMARY_KEYS]
                existing = self.get(primary_key_values)
                if existing:
                    self.update()
                    return

            self.insert()
        except Exception as e:
            logger.error(
                f"Error guardando datos de instrumento {self.__class__.__name__}: {e}"
            )
            raise

    @classmethod
    def get(cls, primary_key_values):
        """Obtiene un registro por su clave primaria"""
        if len(primary_key_values) != len(cls.PRIMARY_KEYS):
            raise ValueError("Número incorrecto de valores de clave primaria")

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        where_clause = " AND ".join([f"{key}=?" for key in cls.PRIMARY_KEYS])
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE {where_clause}"

        try:
            cursor.execute(query, primary_key_values)
            row = cursor.fetchone()

            if row:
                return cls._create_from_row(row)
            return None
        finally:
            conn.close()


# Implementaciones específicas para cada tipo de instrumento
class PCTData(InstrumentDataModel):
    TABLE_NAME = "pct_data"
    COLUMNS = [
        "instrument_id",
        "time",
        "session_id",
        "base_line",
        "pivot",
        "east",
        "north",
        "elevation",
        "diff_time_abs",
        "diff_east_abs",
        "diff_north_abs",
        "diff_vert_abs",
        "diff_horz_abs",
        "diff_disp_total_abs",
        "acum_disp_total_abs",
        "mean_vel_abs",
        "inv_mean_vel_abs",
        "horz_angle_abs_rad",
        "horz_angle_abs_grad",
        "dip_abs_rad",
        "dip_abs_grad",
        "azimuth_abs_grad",
        "diff_time_rel",
        "diff_east_rel",
        "diff_north_rel",
        "diff_vert_rel",
        "diff_horz_rel",
        "diff_disp_total_rel",
        "acum_disp_total_rel",
        "mean_vel_rel",
        "inv_mean_vel_rel",
        "horz_angle_rel_rad",
        "horz_angle_rel_grad",
        "dip_rel_rad",
        "dip_rel_grad",
        "azimuth_rel_grad",
    ]


class PCVData(InstrumentDataModel):
    TABLE_NAME = "pcv_data"
    COLUMNS = [
        "instrument_id",
        "time",
        "session_id",
        "base_line",
        "pivot",
        "digits",
        "temperature",
        "barometric_load",
        "lineal_factor",
        "temperature_factor",
        "sensor_level",
        "terrain_level",
        "diff_time_abs",
        "hydraulic_load_kpa",
        "hydraulic_load_m",
        "piezometric_level",
        "diff_hydraulic_load_abs",
        "mean_vel_hydraulic_load_abs",
        "diff_time_rel",
        "diff_hydraulic_load_rel",
        "mean_vel_hydraulic_load_rel",
    ]


class PTAData(InstrumentDataModel):
    TABLE_NAME = "pta_data"
    COLUMNS = [
        "instrument_id",
        "time",
        "session_id",
        "base_line",
        "pivot",
        "measure",
        "depth",
        "stick_up",
        "bottom_well_elevation",
        "terrain_level",
        "diff_time_abs",
        "water_height",
        "pore_pressure",
        "piezometric_level",
        "diff_water_height_abs",
        "mean_vel_water_height_abs",
        "diff_time_rel",
        "diff_water_height_rel",
        "mean_vel_water_height_rel",
    ]


class SACVData(InstrumentDataModel):
    TABLE_NAME = "sacv_data"
    COLUMNS = [
        "instrument_id",
        "time",
        "session_id",
        "base_line",
        "pivot",
        "digits",
        "temperature",
        "diff_e_res",
        "lineal_factor",
        "temperature_factor",
        "sensor_level",
        "terrain_level",
        "diff_time_abs",
        "settlement_m",
        "settlement_cm",
        "settlement_level",
        "mean_vel_abs",
        "diff_time_rel",
        "mean_vel_rel",
    ]


class CPCVData(InstrumentDataModel):
    TABLE_NAME = "cpcv_data"
    COLUMNS = [
        "instrument_id",
        "time",
        "session_id",
        "base_line",
        "pivot",
        "digits",
        "temperature",
        "lineal_factor",
        "temperature_factor",
        "sensor_level",
        "terrain_level",
        "diff_time_abs",
        "pressure_mpa",
        "pressure_kpa",
        "diff_pressure_abs",
        "mean_vel_pressure_abs",
        "diff_time_rel",
        "diff_pressure_rel",
        "mean_vel_pressure_rel",
    ]


class INCData(InstrumentDataModel):
    TABLE_NAME = "inc_data"
    COLUMNS = [
        "instrument_id",
        "time",
        "session_id",
        "base_line",
        "pivot",
        "a_plus",
        "a_minus",
        "b_plus",
        "b_minus",
        "flevel",
        "a_axis_scale",
        "b_axis_scale",
        "azimuth_rad",
        "enbankment_slope_rad",
        "sensor_level",
        "terrain_level",
        "pipe_length",
        "diff_A",
        "diff_B",
        "check_A",
        "check_B",
        "a_cm",
        "b_cm",
        "a_deflection_raw",
        "b_deflection_raw",
        "a_displacement",
        "b_displacement",
        "elevation",
        "diff_time_abs",
        "a_deflection",
        "b_deflection",
        "a_deflection_vel_abs",
        "b_deflection_vel_abs",
        "diff_time_rel",
        "a_deflection_vel_rel",
        "b_deflection_vel_rel",
    ]


# Funciones de utilidad para manejo de códigos duplicados
def handle_bulk_code_update(model_class, updates):
    """
    Maneja actualizaciones masivas de códigos con manejo de duplicados
    Args:
        model_class: La clase del modelo a actualizar
        updates: Lista de tuplas (id, new_code)
    """
    try:
        for record_id, new_code in updates:
            record = model_class.get(record_id)
            if record:
                old_code = record.code
                record.code = new_code
                record.save()
                logger.info(
                    f"Código actualizado: {old_code} -> {new_code} para {model_class.__name__} ID {record_id}"
                )
    except Exception as e:
        logger.error(f"Error en actualización masiva de códigos: {e}")
        raise


def validate_code_uniqueness(model_class, code, exclude_id=None, **additional_filters):
    """
    Valida si un código es único en el contexto dado
    Args:
        model_class: La clase del modelo a verificar
        code: El código a validar
        exclude_id: ID a excluir de la verificación (para actualizaciones)
        additional_filters: Filtros adicionales basados en UNIQUE_FIELDS
    """
    instance = model_class(code=code, **additional_filters)
    return not instance._code_exists(code, exclude_id)
