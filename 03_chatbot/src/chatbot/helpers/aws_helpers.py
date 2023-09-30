""" Module that contains helper functions for common AWS operations.
"""
import datetime
from typing import Union

import boto3
import botocore
from botocore.credentials import (
    AssumeRoleCredentialFetcher,
    DeferredRefreshableCredentials,
)
from chatbot.config import Iam
from dateutil.tz import tzlocal


def get_current_account_id():
    """Returns the current AWS account ID."""
    account = boto3.client("sts").get_caller_identity()["Account"]
    return account


def _get_client_creator(session):
    def client_creator(service_name, **kwargs):
        return session.client(service_name, **kwargs)

    return client_creator


def assume_role_session(
    role_arn: str, region: str, base_session: botocore.session.Session = None
):
    session = base_session or boto3.Session()
    fetcher = AssumeRoleCredentialFetcher(
        client_creator=_get_client_creator(session),
        source_credentials=session.get_credentials(),
        role_arn=role_arn,
    )
    botocore_session = botocore.session.Session()
    botocore_session._credentials = DeferredRefreshableCredentials(
        method="assume-role", refresh_using=fetcher.fetch_credentials
    )

    return boto3.Session(botocore_session=botocore_session)


def get_boto_session(iam_config: Union[Iam, None], region: str):
    if not iam_config:
        return boto3.Session()
    iam_profile_name = iam_config.parameters.profile or None
    iam_role_arn = iam_config.parameters.role_arn or None

    if iam_profile_name:
        return boto3.Session(profile_name=iam_profile_name)

    if iam_role_arn:
        return assume_role_session(iam_role_arn, region=region)
    return boto3.Session()
