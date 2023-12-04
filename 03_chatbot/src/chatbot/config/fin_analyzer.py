from dataclasses import dataclass
from typing import Any, Optional

from .parser_helpers import from_none, from_str, from_union, to_class, to_enum


@dataclass
class FinAnalyzerParameters:
    friendly_name: str = "Stock Analysis"
    """The name of the RAG option in the menu."""
    s3_bucket: Optional[str] = None
    """S3 bucket with Finance Data."""
    s3_prefix: Optional[str] = None
    """S3 bucket prefix (path) with Finance Data."""

    @staticmethod
    def from_dict(obj: Any) -> "FinAnalyzerParameters":
        assert isinstance(obj, dict)
        friendly_name = from_union([from_str, from_none], obj.get("friendlyName"))
        s3_bucket = from_union([from_str, from_none], obj.get("s3Bucket"))
        s3_prefix = from_union([from_str, from_none], obj.get("s3Prefix"))
        return FinAnalyzerParameters(friendly_name, s3_bucket, s3_prefix)

    def to_dict(self) -> dict:
        result: dict = {}
        result["friendlyName"] = from_union([from_str, from_none], self.friendly_name)
        result["s3Bucket"] = from_union([from_str, from_none], self.s3_bucket)
        result["s3Prefix"] = from_union([from_str, from_none], self.s3_prefix)
        return result


@dataclass
class FinAnalyzer:
    """Configuration for Finance Analyzer."""

    parameters: FinAnalyzerParameters
    type: str

    def __init__(self, parameters: FinAnalyzerParameters):
        self.parameters = parameters
        self.type = FinAnalyzer.typename()

    @classmethod
    def typename(cls) -> str:
        return "FinAnalyzer"

    @staticmethod
    def from_dict(obj: Any) -> "FinAnalyzer":
        assert isinstance(obj, dict)
        parameters = FinAnalyzerParameters.from_dict(obj.get("parameters"))
        type = from_str(obj.get("type"))
        assert type == FinAnalyzer.typename()
        return FinAnalyzer(parameters)

    def to_dict(self) -> dict:
        result: dict = {}
        result["parameters"] = to_class(FinAnalyzerParameters, self.parameters)
        result["type"] = from_str(self.type)
        return result
