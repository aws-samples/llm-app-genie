from dataclasses import dataclass
from functools import partial
from typing import Any

from .parser_helpers import (
    Defaultable,
    from_default,
    from_none,
    from_str,
    from_union,
    to_class,
)

# To use this code, make sure you
#
#     import json
#
# and then, to convert JSON from a string, do
#
#     result = app_config_from_dict(json.loads(json_string))


@dataclass
class AWSsomeChatAppearanceParameters:
    __DEFAULT_FAVICON_URL = "src/aws.png"
    __DEFAULT_NAME = "AWSomeChat"
    """URL or path to image that is the logo for your chat application. Relative to the
    03_chatbot directory.
    """
    favicon_url: str = None
    """The name of your src."""
    name: str = None

    def __init__(self, favicon_url=__DEFAULT_FAVICON_URL, name=__DEFAULT_NAME):
        apply_default_favicon_url = partial(
            from_default, defaultValue=self.__DEFAULT_FAVICON_URL
        )
        apply_default_name = partial(from_default, defaultValue=self.__DEFAULT_NAME)

        self.name = apply_default_name(x=name)
        self.favicon_url = apply_default_favicon_url(x=favicon_url)

    @staticmethod
    def from_dict(obj: Any) -> "AWSsomeChatAppearanceParameters":
        assert isinstance(obj, dict)
        favicon_url = from_union([from_str, from_none], obj.get("faviconUrl"))
        name = from_union([from_str, from_none], obj.get("name"))
        return AWSsomeChatAppearanceParameters(favicon_url, name)

    def to_dict(self) -> dict:
        result: dict = {}
        result["faviconUrl"] = from_union([from_str, from_none], self.favicon_url)
        result["name"] = from_union([from_str, from_none], self.name)
        return result


@dataclass
class AWSsomeChatAppearance:
    pass


@dataclass
class AWSsomeChatAppearance(Defaultable[AWSsomeChatAppearance]):
    """Personalize how the app looks like to your use case."""

    parameters: AWSsomeChatAppearanceParameters
    type: str

    @classmethod
    def typename(cls) -> str:
        return "AWSomeChatAppearance"

    @staticmethod
    def from_dict(obj: Any) -> "AWSsomeChatAppearance":
        assert isinstance(obj, dict)
        type = from_str(obj.get("type"))
        assert type == AWSsomeChatAppearance.typename()
        parameters = AWSsomeChatAppearanceParameters.from_dict(obj.get("parameters"))
        return AWSsomeChatAppearance(parameters, type)

    def to_dict(self) -> dict:
        result: dict = {}
        result["parameters"] = to_class(
            AWSsomeChatAppearanceParameters, self.parameters
        )
        result["type"] = from_str(self.type)
        return result

    @staticmethod
    def from_default(x: Any) -> "AWSsomeChatAppearance":
        params = AWSsomeChatAppearanceParameters()
        return AWSsomeChatAppearance(params, AWSsomeChatAppearance.typename())
