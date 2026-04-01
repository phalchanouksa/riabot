import sys
from pathlib import Path

from rasa.shared.nlu.training_data.message import Message

sys.path.append(str(Path(__file__).resolve().parents[1]))

from khmer_normalizer import KhmerTextNormalizer


def test_khmer_normalizer_standardizes_common_variants():
    normalizer = KhmerTextNormalizer({})
    message = Message(
        data={"text": "  សួស្ដី   bot  អាហារូបករណ៏  ១២៣  "}
    )

    normalizer.process([message])

    assert message.get("text") == "សួស្តី bot អាហារូបករណ៍ 123"
    assert message.get("metadata")["original_text"] == "  សួស្ដី   bot  អាហារូបករណ៏  ១២៣  "


def test_khmer_normalizer_keeps_slash_commands_usable():
    normalizer = KhmerTextNormalizer({})
    message = Message(data={"text": "/START_SURVEY"})

    normalizer.process([message])

    assert message.get("text") == "/start_survey"
