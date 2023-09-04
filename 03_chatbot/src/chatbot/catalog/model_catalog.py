""" Module that contains a model catalog. """
import logging
import time
from dataclasses import dataclass
from typing import List

import boto3
import botocore
from chatbot.config import AmazonBedrock

from .bedrock_model_item import BedrockModelItem
from .catalog import FRIENDLY_NAME_TAG, Catalog
from .sagemaker_model_item import SageMakerModelItem


@dataclass
class ModelCatalog(Catalog):
    """Class for model catalog."""

    regions: List[str]

    bedrock_config: List[AmazonBedrock]

    def __init__(self, regions: list, bedrock_config: List[AmazonBedrock]) -> None:
        # Regions are initialized before the superclass initialization because
        # the superclass initialization will call the _bootstrap method which
        # requires the regions to be initialized
        self.regions = regions
        self.bedrock_config = bedrock_config
        super().__init__()

    def _get_bedrock_models(self):
        """Get list of Bedrock models available in the account."""

        start_time = time.time()
        logging.info("Retrieving Bedrock models in...")
        models = []
        for bedrock_config in self.bedrock_config:
            region = bedrock_config.parameters.region.value
            endpoint_url = bedrock_config.parameters.endpoint_url
            profile = bedrock_config.parameters.profile

            try:
                session = boto3.Session(profile_name=profile)

                bedrock_client = session.client(
                    "bedrock", region, endpoint_url=endpoint_url
                )
                foundation_models = bedrock_client.list_foundation_models()[
                    "modelSummaries"
                ]

                logging.info(foundation_models)
                models += [
                    BedrockModelItem(
                        model_id=fm["modelId"],
                        bedrock_config=bedrock_config.parameters,
                        chat_prompt_identifier="prompts/default_chat.yaml",
                        rag_prompt_identifier="prompts/default_rag.yaml",
                        model_kwargs={"max_tokens_to_sample": 800},
                    )
                    for fm in foundation_models
                ]

            except (
                botocore.exceptions.EndpointConnectionError,
                botocore.exceptions.NoCredentialsError,
            ) as err:
                logging.info(
                    "No Amazon Bedrock models retrieved in %s.\n%s", region, err
                )
            except botocore.exceptions.ClientError as err:
                logging.error(
                    "There was an error while retrieving models from Amazon Bedrock.\n%s",
                    err,
                )
            except botocore.exceptions.UnknownServiceError as err:
                logging.info("Running without Amazon Bedrock.\n%s", err)
        logging.info(
            "%s Bedrock models retrieved in %s seconds",
            len(models),
            time.time() - start_time,
        )
        self += models

    def _get_sagemaker_models(self):
        """Get list of SageMaker models available in the account that are part of Gena."""
        start_time = time.time()
        logging.info("Retrieving SageMaker models...")

        models = []

        for region in self.regions:
            sagemaker_client = boto3.client("sagemaker", region)

            paginator = sagemaker_client.get_paginator("list_endpoints")
            endpoints = paginator.paginate(
                StatusEquals="InService"
            ).build_full_result()["Endpoints"]

            for endpoint in endpoints:
                tags = sagemaker_client.list_tags(ResourceArn=endpoint["EndpointArn"])[
                    "Tags"
                ]
                tags_dict = {tag["Key"]: tag["Value"] for tag in tags}

                if FRIENDLY_NAME_TAG in tags_dict:
                    friendly_name = tags_dict[FRIENDLY_NAME_TAG]

                    chat_prompt_identifier = "prompts/falcon_chat.yaml"
                    if "gena:prompt-chat" in tags_dict:
                        chat_prompt_identifier = tags_dict["gena:prompt-chat"]
                    rag_prompt_identifier = "prompts/falcon_instruct_rag.yaml"
                    if "gena:prompt-rag" in tags_dict:
                        rag_prompt_identifier = tags_dict["gena:prompt-rag"]
                    models.append(
                        SageMakerModelItem(
                            model_name=friendly_name,
                            endpoint_name=endpoint["EndpointName"],
                            region=region,
                            chat_prompt_identifier=chat_prompt_identifier,
                            rag_prompt_identifier=rag_prompt_identifier,
                        )
                    )

        logging.info(
            "%s SageMaker models retrieved in %s seconds",
            len(models),
            time.time() - start_time,
        )
        logging.info(models)

        self += models

    def _bootstrap(self) -> None:
        """Bootstraps the catalog."""
        self._get_bedrock_models()
        self._get_sagemaker_models()
