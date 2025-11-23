import sqlite3

from abc import ABC, abstractmethod
from contextlib import contextmanager

from typing import List, Optional, Dict, Any

from libs.config.config_variables import DATABASE_PATH

from libs.config.config_logger import get_logger

logger = get_logger()


class DatabaseManager:
    """Gestor centralizado de conexiones a base de datos"""

    @staticmethod
    @contextmanager
    def get_connection(db_path: str = None, wal: bool = False, check_same_thread: bool = True):
        """Context manager para conexiones thread-safe y con opciones comunes"""
        path = db_path or DATABASE_PATH
        conn = sqlite3.connect(path, check_same_thread=check_same_thread)
        conn.row_factory = sqlite3.Row
        try:
            if wal:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            # No detener la creación si pragma falla, pero registrar
            logger.debug("No se pudieron aplicar PRAGMA al conectar")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    @contextmanager
    def transaction(db_path: str = None, wal: bool = False, check_same_thread: bool = True):
        """Context manager que devuelve un cursor y maneja commit/rollback"""
        with DatabaseManager.get_connection(db_path=db_path, wal=wal, check_same_thread=check_same_thread) as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            except Exception:
                raise


class Repository(ABC):
    """Patrón Repository para operaciones CRUD"""

    TABLE_NAME: str
    COLUMNS: List[str]
    UNIQUE_FIELDS: List[str] = []

    @classmethod
    def get(cls, id: int) -> Optional[Any]:
        with DatabaseManager.get_connection() as conn:
            row = conn.execute(
                f"SELECT * FROM {cls.TABLE_NAME} WHERE id=?", (id,)
            ).fetchone()
            return cls._row_to_instance(row) if row else None

    @classmethod
    def get_by_field(cls, field: str, value: Any) -> List[Any]:
        with DatabaseManager.get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM {cls.TABLE_NAME} WHERE {field}=?", (value,)
            ).fetchall()
            return [cls._row_to_instance(row) for row in rows]

    @classmethod
    def get_all(cls) -> List[Any]:
        with DatabaseManager.get_connection() as conn:
            rows = conn.execute(f"SELECT * FROM {cls.TABLE_NAME}").fetchall()
            return [cls._row_to_instance(row) for row in rows]

    @classmethod
    @abstractmethod
    def _row_to_instance(cls, row) -> Any:
        pass


class BaseModel(ABC):
    """Clase base abstracta optimizada con patrón Unit of Work"""

    TABLE_NAME: str
    COLUMNS: List[str]
    UNIQUE_FIELDS: List[str] = []

    def __init__(self, **kwargs):
        self._is_dirty = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    def save(self):
        """Guarda el objeto usando Unit of Work pattern"""
        if not self._validate_before_save():
            return False

        try:
            if hasattr(self, "id") and self.id:
                self._update()
            else:
                self._insert()

            self._is_dirty = False
            self._post_save()
            return True

        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error saving {self.__class__.__name__}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error saving {self.__class__.__name__}: {e}")
            raise

    def _validate_before_save(self) -> bool:
        """Validaciones previas al guardado"""
        if hasattr(self, "id") and self.id and not self._exists():
            logger.error(f"{self.__class__.__name__} with id {self.id} does not exist")
            return False
        return True

    def _exists(self) -> bool:
        """Verifica si el registro existe en la base de datos"""
        if not hasattr(self, "id") or not self.id:
            return False

        with DatabaseManager.get_connection() as conn:
            result = conn.execute(
                f"SELECT 1 FROM {self.TABLE_NAME} WHERE id=?", (self.id,)
            ).fetchone()
            return bool(result)

    def _insert(self):
        """Inserta un nuevo registro"""
        data = self._prepare_data()
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))

        with DatabaseManager.get_connection() as conn:
            cursor = conn.execute(
                f"INSERT INTO {self.TABLE_NAME} ({columns}) VALUES ({placeholders})",
                tuple(data.values()),
            )
            self.id = cursor.lastrowid

    def _update(self):
        """Actualiza un registro existente"""
        data = self._prepare_data()
        set_clause = ", ".join([f"{k}=?" for k in data.keys()])

        with DatabaseManager.get_connection() as conn:
            conn.execute(
                f"UPDATE {self.TABLE_NAME} SET {set_clause} WHERE id=?",
                tuple(data.values()) + (self.id,),
            )

    def _prepare_data(self) -> Dict[str, Any]:
        """Prepara datos para inserción/actualización"""
        return {
            k: v
            for k, v in self.__dict__.items()
            if k in self.COLUMNS and k != "id" and not k.startswith("_")
        }

    def _post_save(self):
        """Hook para operaciones post-guardado"""
        pass

    def delete(self):
        """Elimina el registro"""
        if not hasattr(self, "id") or not self.id:
            return

        with DatabaseManager.get_connection() as conn:
            conn.execute(f"DELETE FROM {self.TABLE_NAME} WHERE id=?", (self.id,))

    def refresh(self):
        """Recarga el objeto desde la base de datos"""
        if not hasattr(self, "id") or not self.id:
            return

        with DatabaseManager.get_connection() as conn:
            row = conn.execute(
                f"SELECT * FROM {self.TABLE_NAME} WHERE id=?", (self.id,)
            ).fetchone()

            if row:
                for key in self.COLUMNS:
                    setattr(self, key, row[key])
