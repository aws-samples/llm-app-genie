from dataclasses import dataclass
from typing import Any, Optional

from .parser_helpers import from_none, from_str, from_union, to_class


@dataclass
class IamParameters:
    """Optional credentials profile name to use for access."""

    profile: Optional[str] = None
    """Optional IAM role to assume."""
    role_arn: Optional[str] = None

    @staticmethod
    def from_dict(obj: Any) -> "IamParameters":
        assert isinstance(obj, dict)
        profile = from_union([from_str, from_none], obj.get("profile"))
        role_arn = from_union([from_str, from_none], obj.get("roleARN"))
        return IamParameters(profile, role_arn)

    def to_dict(self) -> dict:
        result: dict = {}
        result["profile"] = from_union([from_str, from_none], self.profile)
        result["roleARN"] = from_union([from_str, from_none], self.role_arn)
        return result


@dataclass
class Iam:
    """Optional IAM configuration to access AWS resources. Supports profile or assuming an IAM
    role.
    """

    parameters: IamParameters
    type: str

    @classmethod
    def typename(cls) -> str:
        return "BotoIAM"

    @staticmethod
    def from_dict(obj: Any) -> "Iam":
        assert isinstance(obj, dict)
        parameters = IamParameters.from_dict(obj.get("parameters"))
        type = from_str(obj.get("type"))
        assert type == Iam.typename()
        return Iam(parameters, type)

    def to_dict(self) -> dict:
        result: dict = {}
        result["parameters"] = to_class(IamParameters, self.parameters)
        result["type"] = from_str(self.type)
        return result
