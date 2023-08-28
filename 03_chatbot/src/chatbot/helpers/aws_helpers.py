""" Module that contains helper functions for common AWS operations.
"""
import boto3


def get_current_account_id():
    """Returns the current AWS account ID."""
    account = boto3.client("sts").get_caller_identity()["Account"]
    return account
