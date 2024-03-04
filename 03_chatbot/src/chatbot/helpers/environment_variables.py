import os
from enum import Enum
from typing import Dict


class ChatbotEnvironmentVariables(Enum):
    """
    The names of all the environment variables the chatbot app uses.
    """

    AmazonBedrockRegion = "BEDROCK_REGION"
    AWSRegion = "AWS_DEFAULT_REGION"
    AmazonTextractS3Bucket = "AMAZON_TEXTRACT_S3_BUCKET"
    BaseUrl = "BASE_URL"
    AWSAppConfigApplication = "AWS_APP_CONFIG_APPLICATION"
    AWSAppConfigEnvironment = "AWS_APP_CONFIG_ENVIRONMENT"
    AWSAppConfigProfile = "AWS_APP_CONFIG_PROFILE"
    AppPrefix = "APP_PREFIX"


class ChatbotEnvironment:
    """
    Access environment variables available to the chatbot without having to provide defaults.

    Central place were all defaults for the environment variables are defined.
    """

    __defaults: Dict[ChatbotEnvironmentVariables, str] = {
        ChatbotEnvironmentVariables.AmazonBedrockRegion: None,
        ChatbotEnvironmentVariables.AWSRegion: "eu-west-1",
        ChatbotEnvironmentVariables.AppPrefix: "genie"
    }

    def get_env_variable(self, variable_name: ChatbotEnvironmentVariables) -> str:
        return os.environ.get(variable_name.value, self.__defaults.get(variable_name))
