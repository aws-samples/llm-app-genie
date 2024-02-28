"""
    Lambda function that implements a CloudFormation custom resource that
    creates an OpenSearch VPC endpoint and adds the endpoint url as a tag to the domain.
"""
import boto3
from typing import List
import uuid
import time

opensearch = boto3.client("opensearch")

def lambda_handler(event, context):
    """
    Lambda function handler that implements the actions when CloudFormation
    requests a resource Create/Update/Delete.
    """
    props = event["ResourceProperties"]
    request_type = event["RequestType"]
    # stack_id = event["StackId"]
    # tags = props["tags"]

    if request_type == "Create":
        endpoint = create_vpc_endpoint(props["domain_arn"], props["subnet_ids"], props["security_group_ids"])

        endpoint = wait_for_vpc_endpoint(endpoint["VpcEndpointId"])

        if "Endpoint" in endpoint:
            endpoint_url = endpoint["Endpoint"]
            add_tag_to_domain(props["domain_arn"], f"{props['app_prefix']}:chatbot_vpc_endpoint" , endpoint_url)
        else:
            raise Exception(f"VPC Endpoint {endpoint['VpcEndpointId']} has no endpoint url")
        vpc_endpoint_id = endpoint["VpcEndpointId"]
    elif request_type == "Update":
        vpc_endpoint_id = event["PhysicalResourceId"]
        endpoint = update_vpc_endpoint(vpc_endpoint_id, props["subnet_ids"], props["security_group_ids"])
        endpoint = wait_for_vpc_endpoint(endpoint["VpcEndpointId"])
        if "Endpoint" in endpoint:
            endpoint_url = endpoint["Endpoint"]
            add_tag_to_domain(props["domain_arn"], f"{props['app_prefix']}:chatbot_vpc_endpoint", endpoint_url)
        vpc_endpoint_id = endpoint["VpcEndpointId"]


    else: # Delete
        vpc_endpoint_id = event["PhysicalResourceId"]
        delete_vpc_endpoint(vpc_endpoint_id)
        remove_tag_from_domain(props["domain_arn"], f"{props['app_prefix']}:chatbot_vpc_endpoint")

    output = {
        'PhysicalResourceId': vpc_endpoint_id,
        # 'Data': {
        #     'CertificateArn': cert_arn
        # }
    }

    return output

def wait_for_vpc_endpoint(vpc_endpoint_id: str, desired_state = "ACTIVE"):
    """
    Waits for the VPC endpoint to be created.
    """
    vpc_endpoint_status = None
    endpoint = None
    while vpc_endpoint_status != desired_state:
        response = opensearch.describe_vpc_endpoints(
            VpcEndpointIds=[vpc_endpoint_id]
        )
        if 'VpcEndpointErrors' in response:
            failed_endpoints = [endpoint for endpoint in response['VpcEndpointErrors'] if endpoint['VpcEndpointId'] == vpc_endpoint_id and endpoint['ErrorCode'] == 'ENDPOINT_NOT_FOUND']
            if len(failed_endpoints) > 0:
                raise Exception(f"VPC Endpoint {vpc_endpoint_id} not found. {failed_endpoints}")
        if 'VpcEndpoints' in response:
            endpoints = [endpoint for endpoint in response['VpcEndpoints'] if endpoint['VpcEndpointId'] == vpc_endpoint_id]
            if len(endpoints) > 0:
                endpoint = endpoints[0]
                vpc_endpoint_status = endpoint['Status']
                failed_states = ['CREATE_FAILED', 'UPDATE_FAILED', 'DELETE_FAILED']
                if vpc_endpoint_status in failed_states:
                    raise Exception(f"VPC Endpoint {vpc_endpoint_id} failed in state {vpc_endpoint_status}")
        time.sleep(10) # Lambda timeout as max waiting time
    return endpoint


def add_tag_to_domain(domain_arn: str, tag_key: str, tag_value: str):
    """
    Adds a tag to the domain.
    """
    opensearch.add_tags(
        ARN=domain_arn,
        TagList=[
            {
                'Key': tag_key,
                'Value': tag_value
            }
        ]
    )

def remove_tag_from_domain(domain_arn: str, tag_key: str):
    """
    Removes a tag from the domain.
    """
    opensearch.remove_tags(
        ARN=domain_arn,
        TagKeys=[tag_key]
    )

def create_vpc_endpoint(domain_arn: str, subnet_ids: List[str], security_group_ids: List[str]):
    """
    Creates a VPC endpoint with the input service name and tags
    """
    response = opensearch.create_vpc_endpoint(
        DomainArn=domain_arn,
        VpcOptions={
            'SubnetIds': subnet_ids,
            'SecurityGroupIds': security_group_ids
        },
        ClientToken=str(uuid.uuid4())
    )


    return response["VpcEndpoint"]


def delete_vpc_endpoint(vpc_endpoint_id: str):
    """
    Deletes a VPC endpoint.
    Throws exception if deletion fails.
    """
    response = opensearch.delete_vpc_endpoint(
        VpcEndpointId=vpc_endpoint_id
    )


    delete_summary = response["VpcEndpointSummary"]
    if delete_summary["Status"] != "DELETING":
        raise Exception(f"VPC Endpoint {vpc_endpoint_id} deletion failed")

def update_vpc_endpoint(vpc_endpoint_id: str, subnet_ids: List[str], security_group_ids: List[str]):
    """
    Updates a VPC endpoint.
    """
    response = opensearch.update_vpc_endpoint(
        VpcEndpointId=vpc_endpoint_id,
        VpcOptions={
            'SubnetIds': subnet_ids,
            'SecurityGroupIds': security_group_ids
        }
    )

    update_output = response["VpcEndpoint"]

    if update_output["Status"] == "UPDATE_FAILED":
        raise Exception(f"VPC Endpoint {vpc_endpoint_id} update failed")

    return update_output


# event = {
#     'ResourceProperties': {
#                 "domain_arn": "arn:aws:es:REGION:ACCOUNT_ID:domain/xxxxxxxxxxx",
#                 "app_prefix": "Genie",
#                 "subnet_ids": ["subnet-xxxxxxxxxxxxxxxxx","subnet-xxxxxxxxxxxxxxxxx"],
#                 "security_group_ids": ["sg-xxxxxxxxxxxxxxxx"]
#             },
#     'RequestType': 'Create'
# }
# print(lambda_handler(event, None))