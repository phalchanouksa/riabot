import typing
from typing import Any, Optional, Text, Dict, List, Type

from rasa.engine.graph import ExecutionContext
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.nlu.tokenizers.tokenizer import Token, Tokenizer
from rasa.shared.nlu.training_data.message import Message

import khmernltk

@DefaultV1Recipe.register(
    DefaultV1Recipe.ComponentType.MESSAGE_TOKENIZER, is_trainable=False
)
class KhmerTokenizer(Tokenizer):
    """A custom Tokenizer that uses khmernltk for segmenting Khmer text."""

    def __init__(self, config: Dict[Text, Any]) -> None:
        """Initializes the tokenizer."""
        super().__init__(config)

    @classmethod
    def create(
        cls,
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
    ) -> "KhmerTokenizer":
        """Creates a new component."""
        return cls(config)

    def tokenize(self, message: Message, attribute: Text) -> List[Token]:
        """Tokenizes the text of the provided attribute of the incoming message."""
        text = message.get(attribute)
        if not text:
            return []

        # Split the text using khmernltk
        segmented_text = khmernltk.word_tokenize(text, return_tokens=True)
        
        # Build Rasa Tokens
        tokens = []
        running_offset = 0
        for word in segmented_text:
            # find the actual position in the original text to maintain correct offsets
            start = text.find(word, running_offset)
            if start == -1:
                # If exact word not found because of some normalization, estimate it
                start = running_offset
            
            end = start + len(word)
            tokens.append(Token(word, start))
            running_offset = end

        return tokens
