from typing import Optional

from .base import BaseModel
from .translation import TranslatableMixin
from .file_system import FileSystemManager, PathBuilder

from libs.config.config_variables import STORAGE_DIR


class MiningUnit(TranslatableMixin, BaseModel):
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
    UNIQUE_FIELDS = ["client_id", "code"]
    TRANSLATION_PREFIX = "mining_unit"

    def __init__(self, client_code: Optional[str] = None, **kwargs):
        if client_code and "client_id" not in kwargs:
            from .client import Client

            client = Client.get_by_code(client_code)
            if client:
                kwargs["client_id"] = client.id

        super().__init__(**kwargs)
        self._update_paths()

    def _update_paths(self):
        client = self._get_client()
        if client and hasattr(self, "code"):
            builder = PathBuilder(STORAGE_DIR)
            self.geometries_path = builder.add(
                "geometries", client.code, self.code
            ).build()
            self.documentation_path = builder.add(
                "documentation", client.code, self.code
            ).build()

    def _get_client(self):
        from .client import Client

        return Client.get(self.client_id) if hasattr(self, "client_id") else None

    def _post_save(self):
        self.create_associated_folders()

    def create_associated_folders(self):
        for path in [self.geometries_path, self.documentation_path]:
            FileSystemManager.create_folder(path)

        # Subcarpetas de geometrías
        subfolders = ["polylines", "surfaces", "sections", "ortophotos"]
        for folder in subfolders:
            FileSystemManager.create_folder(
                PathBuilder(self.geometries_path).add(folder).build()
            )
