import os
import shutil

from libs.config.config_logger import get_logger
from libs.helpers.storage_helpers import validate_folder

logger = get_logger()


class FileSystemManager:
    """Gestor de operaciones del sistema de archivos con patrón Strategy"""

    @staticmethod
    def create_folder(path: str) -> bool:
        if not path or os.path.exists(path):
            return False

        try:
            validate_folder(path, create_if_missing=True)
            logger.debug(f"Folder created: {path}")
            return True
        except OSError as e:
            logger.error(f"Error creating folder {path}: {e}")
            return False

    @staticmethod
    def rename_folder(old_path: str, new_path: str) -> bool:
        if (
            not all([old_path, new_path])
            or not os.path.exists(old_path)
            or os.path.exists(new_path)
        ):
            return False

        try:
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            os.rename(old_path, new_path)
            logger.debug(f"Folder renamed: {old_path} -> {new_path}")
            return True
        except OSError as e:
            logger.error(f"Error renaming folder {old_path}: {e}")
            return False

    @staticmethod
    def delete_folder(path: str) -> bool:
        if not path or not os.path.exists(path):
            return False

        try:
            shutil.rmtree(path)
            logger.debug(f"Folder deleted: {path}")
            return True
        except OSError as e:
            logger.error(f"Error deleting folder {path}: {e}")
            return False


class PathBuilder:
    """Builder pattern para construir rutas consistentes"""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self._parts = []

    def add(self, *parts: str) -> "PathBuilder":
        self._parts.extend(part for part in parts if part)
        return self

    def build(self) -> str:
        return os.path.join(self.base_dir, *self._parts)
