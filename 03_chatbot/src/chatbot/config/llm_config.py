from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .parser_helpers import (
    from_dict,
    from_float,
    from_int,
    from_list,
    from_none,
    from_str,
    from_union,
    to_class,
    to_float,
)


@dataclass
class LLMConfigParameters:
    """Local path, S3 URI or LangChainHub path that contains prompt template to use when
    chatting with this model.
    """

    chat_prompt: Optional[str] = None
    """Configures the max number of tokens to use in the generated response."""
    max_token_count: Optional[int] = None
    """Local path, S3 URI or LangChainHub path that contains prompt template to use when asking
    questions based on documents to this model.
    """
    rag_prompt: Optional[str] = None
    """Make the model stop at a desired word or character, such as the end of a sentence or a
    list.
    """
    stop_sequence: Optional[List[str]] = None
    """A lower value results in more deterministic responses, whereas a higher value results in
    more random responses.
    """
    temperature: Optional[float] = None
    """Controls token choices, based on the probability of the potential choices. If you set Top
    P below 1.0, the model considers only the most probable options and ignores less probable
    options. The result is more stable and repetitive completions.
    """
    top_p: Optional[float] = None

    @staticmethod
    def from_dict(obj: Any) -> "LLMConfigParameters":
        assert isinstance(obj, dict)
        chat_prompt = from_union([from_str, from_none], obj.get("chatPrompt"))
        max_token_count = from_union([from_int, from_none], obj.get("maxTokenCount"))
        rag_prompt = from_union([from_str, from_none], obj.get("ragPrompt"))
        stop_sequence = from_union(
            [lambda x: from_list(from_str, x), from_none], obj.get("stopSequence")
        )
        temperature = from_union([from_float, from_none], obj.get("temperature"))
        top_p = from_union([from_float, from_none], obj.get("topP"))
        return LLMConfigParameters(
            chat_prompt, max_token_count, rag_prompt, stop_sequence, temperature, top_p
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["chatPrompt"] = from_union([from_str, from_none], self.chat_prompt)
        result["maxTokenCount"] = from_union(
            [from_int, from_none], self.max_token_count
        )
        result["ragPrompt"] = from_union([from_str, from_none], self.rag_prompt)
        result["stopSequence"] = from_union(
            [lambda x: from_list(from_str, x), from_none], self.stop_sequence
        )
        result["temperature"] = from_union([to_float, from_none], self.temperature)
        result["topP"] = from_union([to_float, from_none], self.top_p)
        return result


@dataclass
class LLMConfig:
    """Configuration for a large language model."""

    parameters: LLMConfigParameters
    type: str

    def __init__(self, parameters: LLMConfigParameters):
        self.parameters = parameters
        self.type = LLMConfig.typename()

    @classmethod
    def typename(cls) -> str:
        return "LLMConfig"

    @staticmethod
    def from_dict(obj: Any) -> "LLMConfig":
        assert isinstance(obj, dict)
        parameters = LLMConfigParameters.from_dict(obj.get("parameters"))
        type = from_str(obj.get("type"))
        assert type == LLMConfig.typename()
        return LLMConfig(parameters)

    def to_dict(self) -> dict:
        result: dict = {}
        result["parameters"] = to_class(LLMConfigParameters, self.parameters)
        result["type"] = from_str(self.type)
        return result


@dataclass
class LLMConfigMap:
    """Maps large language models identifiers to their configuration."""

    parameters: Dict[str, LLMConfig]
    type: str

    def __init__(self, parameters: Dict[str, LLMConfig]):
        self.parameters = parameters
        self.type = LLMConfigMap.typename()

    @classmethod
    def typename(cls) -> str:
        return "LLMConfigMap"

    @staticmethod
    def from_dict(obj: Any) -> "LLMConfigMap":
        assert isinstance(obj, dict)
        parameters = from_dict(LLMConfig.from_dict, obj.get("parameters"))
        type = from_str(obj.get("type"))
        assert type == LLMConfigMap.typename()
        return LLMConfigMap(parameters)

    def to_dict(self) -> dict:
        result: dict = {}
        result["parameters"] = from_dict(
            lambda x: to_class(LLMConfig, x), self.parameters
        )
        result["type"] = from_str(self.type)
        return result
