from typing import List

from .base import BaseModel
from .translation import TranslatableMixin
from .file_system import FileSystemManager, PathBuilder

from libs.config.config_variables import STORAGE_DIR


class Client(TranslatableMixin, BaseModel):
    TABLE_NAME = "client"
    COLUMNS = ["id", "name_key_id", "code", "logo_path"]
    UNIQUE_FIELDS = ["code"]
    TRANSLATION_PREFIX = "client"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_paths()

    def _update_paths(self):
        if hasattr(self, "code") and self.code:
            self.logo_path = PathBuilder(STORAGE_DIR).add("logos", self.code).build()

    def _post_save(self):
        self.create_associated_folders()

    def create_associated_folders(self):
        FileSystemManager.create_folder(self.logo_path)

    def get_mining_units(self) -> List:
        from .mining_unit import MiningUnit

        return (
            MiningUnit.get_by_field("client_id", self.id) if hasattr(self, "id") else []
        )
