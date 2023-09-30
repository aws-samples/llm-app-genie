from dataclasses import dataclass
from typing import Any, Optional

from .aws_region import AWSRegion
from .iam import Iam
from .parser_helpers import from_none, from_str, from_union, to_class, to_enum


@dataclass
class AmazonBedrockParameters:
    region: AWSRegion
    """AWS Region to access Amazon Bedrock."""
    endpoint_url: Optional[str] = None
    """Optional endpoint url to access Amazon Bedrock."""
    iam: Optional[Iam] = None
    """Optional IAM configuration to access Amazon Bedrock."""

    @staticmethod
    def from_dict(obj: Any) -> "AmazonBedrockParameters":
        assert isinstance(obj, dict)
        region = AWSRegion(obj.get("region"))
        endpoint_url = from_union([from_str, from_none], obj.get("endpointURL"))
        iam = from_union([Iam.from_dict, from_none], obj.get("iam"))
        return AmazonBedrockParameters(region, endpoint_url, iam)

    def to_dict(self) -> dict:
        result: dict = {}
        result["region"] = to_enum(AWSRegion, self.region)
        result["endpointURL"] = from_union([from_str, from_none], self.endpoint_url)
        result["iam"] = from_union([lambda x: to_class(Iam, x), from_none], self.iam)
        return result


@dataclass
class AmazonBedrock:
    """Optional Configuration for Amazon Bedrock."""

    parameters: AmazonBedrockParameters
    type: str

    def __init__(self, parameters: AmazonBedrockParameters):
        self.parameters = parameters
        self.type = AmazonBedrock.typename()

    @classmethod
    def typename(cls) -> str:
        return "AmazonBedrock"

    @staticmethod
    def from_dict(obj: Any) -> "AmazonBedrock":
        assert isinstance(obj, dict)
        parameters = AmazonBedrockParameters.from_dict(obj.get("parameters"))
        type = from_str(obj.get("type"))
        assert type == AmazonBedrock.typename()
        return AmazonBedrock(parameters)

    def to_dict(self) -> dict:
        result: dict = {}
        result["parameters"] = to_class(AmazonBedrockParameters, self.parameters)
        result["type"] = from_str(self.type)
        return result
