import re
import unicodedata
from typing import Any, Dict, List, Text

from rasa.engine.graph import ExecutionContext, GraphComponent
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.training_data.training_data import TrainingData


_WHITESPACE_TRANSLATION = str.maketrans(
    {
        "\u00a0": " ",
        "\u200b": " ",
        "\u200c": "",
        "\u200d": "",
        "\ufeff": "",
        "\u2060": "",
    }
)

_KHMER_DIGIT_TRANSLATION = str.maketrans("០១២៣៤៥៦៧៨៩", "0123456789")

_DEFAULT_REPLACEMENTS = {
    "សួស្ដី": "សួស្តី",
    "ជំរាបសួរ": "ជម្រាបសួរ",
    "ជំរាបសួរបាទ": "ជម្រាបសួរបាទ",
    "ចាប់ផ្ដើម": "ចាប់ផ្តើម",
    "គូររៀន": "គួររៀន",
    "គូរជ្រើស": "គួរជ្រើស",
    "ធ្វេី": "ធ្វើ",
    "ធេ្វី": "ធ្វើ",
    "តេី": "តើ",
    "អេី": "អើ",
    "ឈ្មោះអី": "ឈ្មោះអ្វី",
    "អាហារូបករណ៏": "អាហារូបករណ៍",
    "អាហារូបករន៍": "អាហារូបករណ៍",
}


@DefaultV1Recipe.register(
    [DefaultV1Recipe.ComponentType.MESSAGE_FEATURIZER], is_trainable=False
)
class KhmerTextNormalizer(GraphComponent):
    """Normalizes Khmer and mixed Khmer/English user text before tokenization."""

    @staticmethod
    def get_default_config() -> Dict[Text, Any]:
        return {
            "normalize_latin_case": True,
            "normalize_khmer_digits": True,
            "collapse_whitespace": True,
            "normalize_punctuation": True,
            "variant_replacements": _DEFAULT_REPLACEMENTS,
        }

    def __init__(self, config: Dict[Text, Any]) -> None:
        self._config = {**self.get_default_config(), **config}
        replacements = self._config.get("variant_replacements") or {}
        self._ordered_replacements = sorted(
            replacements.items(), key=lambda item: len(item[0]), reverse=True
        )

    @classmethod
    def create(
        cls,
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
    ) -> "KhmerTextNormalizer":
        return cls(config)

    def process_training_data(self, training_data: TrainingData) -> TrainingData:
        self.process(training_data.training_examples)
        return training_data

    def process(self, messages: List[Message]) -> List[Message]:
        for message in messages:
            text = message.get("text")
            if not text:
                continue

            normalized_text = self._normalize_text(text)
            if normalized_text == text:
                continue

            metadata = dict(message.get("metadata") or {})
            metadata.setdefault("original_text", text)
            metadata["normalized_text"] = normalized_text
            message.set("metadata", metadata)
            message.set("text", normalized_text)

        return messages

    def _normalize_text(self, text: Text) -> Text:
        normalized = unicodedata.normalize("NFC", text)
        normalized = normalized.translate(_WHITESPACE_TRANSLATION)

        if self._config.get("normalize_latin_case", True):
            normalized = normalized.lower()

        if self._config.get("normalize_khmer_digits", True):
            normalized = normalized.translate(_KHMER_DIGIT_TRANSLATION)

        if self._config.get("normalize_punctuation", True):
            normalized = re.sub(r"[។៕]+", "។", normalized)
            normalized = re.sub(r"[?？]+", "?", normalized)
            normalized = re.sub(r"[!！]+", "!", normalized)
            normalized = re.sub(r"[,，]+", ",", normalized)
            normalized = re.sub(r"\s+([?!,។៖])", r"\1", normalized)

        for source, target in self._ordered_replacements:
            normalized = normalized.replace(source, target)

        if self._config.get("collapse_whitespace", True):
            normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized
