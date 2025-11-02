import random
import string

from typing import Optional
from datetime import datetime

from .base import BaseModel
from .file_system import FileSystemManager, PathBuilder

from libs.config.config_variables import STORAGE_DIR


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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "session_code"):
            self.session_code = None
        self._ensure_paths()

    def _ensure_paths(self):
        """Garantiza que todas las rutas estén definidas"""
        paths = {
            "raw_data_path": self._build_data_path("raw_data"),
            "temp_path": self._build_data_path("temp"),
            "outputs_path": self._build_data_path("outputs"),
        }

        for attr, path in paths.items():
            if not hasattr(self, attr) or not getattr(self, attr):
                setattr(self, attr, path)

    def _build_data_path(self, data_type: str) -> Optional[str]:
        project = self._get_project()
        if not project:
            return None

        mining_unit = project.get_mining_unit()
        client = mining_unit.get_client() if mining_unit else None

        if all([client, mining_unit, self.session_code]):
            return (
                PathBuilder(STORAGE_DIR)
                .add(data_type, client.code, mining_unit.code, self.session_code)
                .build()
            )
        return None

    def save(self):
        if not hasattr(self, "created_at") or not self.created_at:
            self.created_at = datetime.now().isoformat()

        if not self.session_code:
            self._generate_session_code()
            self._ensure_paths()

        super().save()

    def _generate_session_code(self):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_chars = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=8)
        )
        self.session_code = f"{timestamp}-{random_chars}"

    def _post_save(self):
        self.create_associated_folders()

    def create_associated_folders(self):
        for path_attr in ["temp_path", "outputs_path", "raw_data_path"]:
            if hasattr(self, path_attr):
                FileSystemManager.create_folder(getattr(self, path_attr))
