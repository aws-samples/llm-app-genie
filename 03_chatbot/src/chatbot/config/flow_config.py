from dataclasses import dataclass
from typing import Any, Optional

from .parser_helpers import from_dict, from_none, from_str, from_union, to_class, to_enum


@dataclass
class FlowConfigParameters:
    """Flow confitufation dictionary."""
    flows: dict
    rag: dict

    @staticmethod
    def from_dict(obj: Any) -> "FlowConfigParameters":
        assert isinstance(obj, dict)
        flows = from_union([lambda x: from_dict(dict, x), from_none], obj.get("flows"))
        rag = obj.get("rag")
        # s3_bucket = from_union([from_str, from_none], obj.get("s3Bucket"))
        return FlowConfigParameters(flows, rag)

    def to_dict(self) -> dict:
        result: dict = {}
        result["flows"] = from_union([lambda x: from_dict(dict, x), from_none], self.flows) 
        result["rag"] = self.rag
        # result["s3Bucket"] = from_union([from_str, from_none], self.s3_bucket)
        return result


@dataclass
class FlowConfig:
    """Configuration for Finance Analyzer."""

    parameters: FlowConfigParameters
    type: str

    def __init__(self, parameters: FlowConfigParameters):
        self.parameters = parameters
        self.type = FlowConfig.typename()

    @classmethod
    def typename(cls) -> str:
        return "FlowConfig"

    @staticmethod
    def from_dict(obj: Any) -> "FlowConfig":
        assert isinstance(obj, dict)
        parameters = FlowConfigParameters.from_dict(obj.get("parameters"))
        type = from_str(obj.get("type"))
        assert type == FlowConfig.typename()
        return FlowConfig(parameters)

    def to_dict(self) -> dict:
        result: dict = {}
        result["parameters"] = to_class(FlowConfigParameters, self.parameters)
        result["type"] = from_str(self.type)
        return result
