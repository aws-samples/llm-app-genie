"""
    Lambda function that implements an is complete check on a Kendra Data Source custom resource.
"""

import boto3

kendra = boto3.client('kendra')

def lambda_handler(event, context):
    physical_id = event["PhysicalResourceId"]

    is_complete = False

    request_type = event['RequestType'].lower()
    props = event['ResourceProperties']
    
    exception = None
    response = None

    try:
        response = kendra.describe_data_source(
            Id=physical_id,
            IndexId=props['index_id']
        )
    except kendra.exceptions.ResourceNotFoundException as ex:
        exception = ex

    if request_type == 'create':

        if type(exception) is kendra.exceptions.ResourceNotFoundException:
            is_complete = False
        else:
            if response is not None:
                is_complete = True if response['Status'] == "ACTIVE" else False

    if request_type == 'update':
        if type(exception) is kendra.exceptions.ResourceNotFoundException:
            is_complete = True
        else:
            if response is not None:
                is_complete = False if response['Status'] == "UPDATING" else True
    if request_type == 'delete':
        if type(exception) is kendra.exceptions.ResourceNotFoundException:
            is_complete = True
        else:
            is_complete = False
        
    return { 'IsComplete': is_complete }

