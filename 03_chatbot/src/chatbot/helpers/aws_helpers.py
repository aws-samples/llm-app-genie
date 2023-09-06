""" Module that contains helper functions for common AWS operations.
"""
from typing import Union

import boto3
from chatbot.config import Iam


def get_current_account_id():
    """Returns the current AWS account ID."""
    account = boto3.client("sts").get_caller_identity()["Account"]
    return account


def get_boto_session(iam_config: Union[Iam, None]):
    if not iam_config:
        return boto3.Session()
    iam_profile_name = iam_config.parameters.profile or None
    iam_role_arn = iam_config.parameters.role_arn or None

    if iam_profile_name:
        return boto3.Session(profile_name=iam_profile_name)

    if iam_role_arn:
        # session = boto3.Session(profile_name=profile)
        sts_client = boto3.client("sts")

        assumed_role_object = sts_client.assume_role(
            RoleArn=iam_role_arn, RoleSessionName="ChatbotSession"
        )

        # From the response that contains the assumed role, get the temporary
        # credentials that can be used to make subsequent API calls
        credentials = assumed_role_object["Credentials"]

        # session = boto3.Session(
        #     profile_name=profile
        # )

        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

    return boto3.Session()
