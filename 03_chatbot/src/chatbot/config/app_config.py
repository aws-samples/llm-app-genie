import json
import logging
import os
from dataclasses import dataclass
from typing import Any, List, Optional

from appconfig_helper import AppConfigHelper
from chatbot.helpers import ChatbotEnvironment, ChatbotEnvironmentVariables

from .aws_region import AWSRegion
from .config_amazon_bedrock import AmazonBedrock, AmazonBedrockParameters
from .config_appearance import AWSsomeChatAppearance
from .parser_helpers import from_list, from_none, from_union, to_class

# This code is used to parse the configuration file for this application.
# Before making changes you should read ./json_schema/Readme.
#
# To use this code, make sure you
#
#     import json
#
# and then, to convert JSON from a string, do
#
#     result = app_config_from_dict(json.loads(json_string))


LOCAL_DEV_APPCONFIG_JSON_PATH = "../appconfig.json"


@dataclass
class AppConfig:
    """App configuration for the AWSomeChat application."""

    _amazon_bedrock: Optional[List[AmazonBedrock]] = None
    appearance: AWSsomeChatAppearance = None

    def __init__(
        self,
        appearance: AWSsomeChatAppearance,
        amazon_bedrock: Optional[List[AmazonBedrock]] = None,
    ):
        self.appearance = appearance
        self._amazon_bedrock = amazon_bedrock

    @property
    def amazon_bedrock(self) -> Optional[List[AmazonBedrock]]:
        return self._amazon_bedrock

    def add_amazon_bedrock(self, region: AWSRegion, endpoint_url: str = None):
        """Adds an AWS Region for Amazon Bedrock usage to the config.

        If the region is already configured, it will be ignored.

        :param region: AWS Region for Amazon Bedrock usage.
        :param endpoint_url: Optional endpoint URL for Amazon Bedrock usage.
        """
        new_bedrock_config = AmazonBedrock(
            AmazonBedrockParameters(region, endpoint_url)
        )
        if self._amazon_bedrock is None:
            self._amazon_bedrock = [new_bedrock_config]
        elif not any(
            existing_bedrock.parameters.region == region
            for existing_bedrock in self._amazon_bedrock
        ):
            # Only append if Amazon Bedrock region has not already been configured.
            self._amazon_bedrock.append(new_bedrock_config)

    @staticmethod
    def from_dict(obj: Any) -> "AppConfig":
        assert isinstance(obj, dict)
        appearance = from_union(
            [AWSsomeChatAppearance.from_dict, AWSsomeChatAppearance.from_default],
            obj.get("appearance"),
        )
        amazon_bedrock = from_union(
            [lambda x: from_list(AmazonBedrock.from_dict, x), from_none],
            obj.get("amazonBedrock", []),
        )
        return AppConfig(appearance=appearance, amazon_bedrock=amazon_bedrock)

    def to_dict(self) -> dict:
        result: dict = {}
        result["appearance"] = to_class(AWSsomeChatAppearance, self.appearance)
        result["amazonBedrock"] = from_union(
            [lambda x: from_list(lambda x: to_class(AmazonBedrock, x), x), from_none],
            self.amazon_bedrock,
        )

        return result


def app_config_from_dict(s: Any) -> AppConfig:
    return AppConfig.from_dict(s)


def app_config_to_dict(x: AppConfig) -> Any:
    return to_class(AppConfig, x)


class AppConfigProvider:
    __config: AppConfig = None

    def __init__(self, environment: ChatbotEnvironment) -> None:
        aws_app_config_app_name = environment.get_env_variable(
            ChatbotEnvironmentVariables.AWSAppConfigApplication
        )
        aws_app_config_env_name = environment.get_env_variable(
            ChatbotEnvironmentVariables.AWSAppConfigEnvironment
        )
        aws_app_config_profile_name = environment.get_env_variable(
            ChatbotEnvironmentVariables.AWSAppConfigProfile
        )
        if (
            aws_app_config_app_name is not None
            and aws_app_config_env_name is not None
            and aws_app_config_profile_name is not None
        ):
            # Use AWS AppConfig
            max_config_age = 120
            fetch_on_init = False
            fetch_on_read = True
            appconfig = AppConfigHelper(
                appconfig_application=aws_app_config_app_name,
                appconfig_environment=aws_app_config_env_name,
                appconfig_profile=aws_app_config_profile_name,
                max_config_age=max_config_age,
                fetch_on_init=fetch_on_init,
                fetch_on_read=fetch_on_read,
            )
            self.__config = app_config_from_dict(appconfig.config)
        else:
            # Use local config
            script_dir = os.path.dirname(__file__)
            abs_file_path = os.path.join(script_dir, LOCAL_DEV_APPCONFIG_JSON_PATH)
            logging.info(f"Using local config file: {abs_file_path}")
            with open(abs_file_path, "r") as j:
                self.__config = app_config_from_dict(json.load(j))

    @property
    def config(self) -> AppConfig:
        """The application configuration content."""
        return self.__config
