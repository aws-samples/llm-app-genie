"""
    Lambda function that implements a Kendra Data Source custom resource that
    creates a Kendra Data Source.
"""
import boto3
import json

kendra = boto3.client("kendra")


def lambda_handler(event, context):
    """
    Lambda function handler that implements the actions when CloudFormation
    requests a resource Create/Update/Delete.
    """
    props = event["ResourceProperties"]
    request_type = event["RequestType"]
    tags = props["tags"]

    config = json.loads(props["config"])

    if request_type == "Create":
        data_source_id = create_data_source(name=props["name"], index_id=props["index_id"], config=config, role_arn=props["role_arn"], tags=tags)
    elif request_type == "Update":
        # Deletes and regenerates a self-signed certificate
        data_source_id = event["PhysicalResourceId"]
        index_id = props["index_id"]
        region = props["region"]
        account_id = props["account_id"]

        data_source_arn = f"arn:aws:kendra:{region}:{account_id}:index/{index_id}/data-source/{data_source_id}"

        update_data_source(name=props["name"], index_id=index_id, config=config, data_source_id=data_source_id)
        update_tags(data_source_arn=data_source_arn, tags=tags)


    else: # Delete
        data_source_id = event["PhysicalResourceId"]
        delete_data_source(props["index_id"], data_source_id)

    output = {
        'PhysicalResourceId': data_source_id
    }

    return output


def create_data_source(name: str, index_id: str, config, role_arn: str, tags: list[dict[str, str]]) -> str:
    """
    Creates a data source in Kendra.
    """
    response = kendra.create_data_source(
        Name=name,
        IndexId=index_id,
        Type="TEMPLATE",
        Configuration=config,
        RoleArn=role_arn,
        Tags=tags
    )
    return response["Id"]

def update_data_source(name: str, index_id: str, config, data_source_id: str) -> None:
    """
    Updates a data source in Kendra.
    """
    kendra.update_data_source(
        Id=data_source_id,
        Configuration=config,
        Name=name,
        IndexId=index_id
    )

def delete_data_source(index_id: str, data_source_id: str) -> None:
    """
    Deletes a data source in Kendra.
    """
    kendra.delete_data_source(
        Id=data_source_id,
        IndexId=index_id
    )   


def update_tags(data_source_arn: str, tags: list[dict[str, str]]) -> None:
    """
    Updates the tags of a data source in Kendra.
    """
    response = kendra.list_tags_for_resource(
        ResourceARN=data_source_arn
    )
    current_tags = response["Tags"]
    tag_keys = [tag["Key"] for tag in current_tags]
    new_tag_keys = [tag["Key"] for tag in tags]
    keys_to_delete = list(set(tag_keys) - set(new_tag_keys))
    
    if len(keys_to_delete) > 0:
        kendra.untag_resource(
            ResourceARN=data_source_arn,
            TagKeys=keys_to_delete
        )

    if len(tags) > 0:
        kendra.tag_resource(
            ResourceARN=data_source_arn,
            Tags=tags
        )