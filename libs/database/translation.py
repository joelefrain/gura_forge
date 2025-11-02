from typing import Dict, Optional

from .base import BaseModel, Repository, DatabaseManager


class TranslationKey(BaseModel, Repository):
    TABLE_NAME = "translation_key"
    COLUMNS = ["id", "key_name"]
    UNIQUE_FIELDS = ["key_name"]

    @classmethod
    def _row_to_instance(cls, row):
        return cls(**dict(row))

    @classmethod
    def get_by_name(cls, key_name: str) -> Optional["TranslationKey"]:
        results = cls.get_by_field("key_name", key_name)
        return results[0] if results else None


class Translation(BaseModel, Repository):
    TABLE_NAME = "translation"
    COLUMNS = ["key_id", "language_code", "translated_text"]

    @classmethod
    def _row_to_instance(cls, row):
        return cls(**dict(row))

    @classmethod
    def upsert(cls, key_id: int, language_code: str, translated_text: str):
        with DatabaseManager.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO translation 
                (key_id, language_code, translated_text) 
                VALUES (?, ?, ?)
            """,
                (key_id, language_code, translated_text),
            )

    @classmethod
    def get_by_key_id(cls, key_id: int) -> Dict[str, str]:
        translations = cls.get_by_field("key_id", key_id)
        return {t.language_code: t.translated_text for t in translations}


class TranslatableMixin:
    """Mixin para modelos que necesitan traducciones"""

    TRANSLATION_PREFIX: str = None

    def __init__(self, name_translations: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.name_translations = name_translations or {}
        self._name_key_id = kwargs.get("name_key_id")

    def _create_translation_key(self):
        if not self.TRANSLATION_PREFIX or not hasattr(self, "code"):
            return

        base_key = f"{self.TRANSLATION_PREFIX}_{self.code}"
        key = TranslationKey(key_name=base_key)
        key.save()
        self._name_key_id = key.id

    def _save_translations(self):
        if not self._name_key_id:
            return

        for lang, text in self.name_translations.items():
            if text:
                Translation.upsert(self._name_key_id, lang, text)

    def get_name(self, language_code: str = "es") -> Optional[str]:
        if not self._name_key_id:
            return None

        translations = Translation.get_by_key_id(self._name_key_id)
        return translations.get(language_code) or next(
            iter(translations.values()), None
        )
