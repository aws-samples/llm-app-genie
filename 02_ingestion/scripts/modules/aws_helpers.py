import json
import boto3
from botocore.config import Config
import os
from io import StringIO
import pandas as pd

global s3_client

region = os.environ.get('AWS_REGION') 
if not region:
    region = "eu-west-1"

config = Config(region_name=region)

ssm_client = boto3.client("ssm")
secmgr_client = boto3.client("secretsmanager", config=config)
s3_client = boto3.client("s3", config=config)

# Get the parameter value
def get_parameter_value(parameter_name, decrypt=True):
    response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=decrypt)
    return response["Parameter"]["Value"]

# get secret from secret manager
def get_credentials(secret_id: str) -> str:
    response = secmgr_client.get_secret_value(SecretId=secret_id)
    secrets_value = json.loads(response["SecretString"])
    return secrets_value

# Loading the data from S3
def read_from_s3(bucket, key, format):
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    data = obj['Body'].read().decode('utf-8')

    if format == "csv":
        return pd.read_csv(StringIO(data))
    elif format == "json":
        return pd.read_json(StringIO(data))