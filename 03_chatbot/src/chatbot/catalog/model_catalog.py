""" Module that contains a model catalog. """
import re
import time
from dataclasses import dataclass
from logging import Logger, getLogger
from typing import Dict, List, Optional

import boto3
import botocore
from chatbot.config import AmazonBedrock, LLMConfig, FlowConfig
from chatbot.helpers import get_boto_session

from .model_catalog_item_bedrock import BedrockModelItem
from .catalog import FRIENDLY_NAME_TAG, Catalog
from .model_catalog_item_sagemaker import SageMakerModelItem


@dataclass
class ModelCatalog(Catalog):
    """Class for model catalog."""

    regions: List[str]

    bedrock_config: List[AmazonBedrock]

    llm_config: Dict[str, LLMConfig]

    logger: Logger

    def __init__(
        self,
        regions: list,
        bedrock_config: List[AmazonBedrock],
        llm_config: Dict[str, LLMConfig],
        logger: Logger = getLogger("ModelCatalogLogger"),
        callbacks = []
    ) -> None:
        self.regions = regions
        self.bedrock_config = bedrock_config
        self.logger = logger
        self.llm_config = llm_config
        self.callbacks = callbacks
        super().__init__()

    def get_llm_config(
        self, model_id, config_model_id_regexs: List[re.Pattern]
    ) -> Optional[LLMConfig]:
        if model_id in self.llm_config:
            return self.llm_config[model_id]

        for regex in config_model_id_regexs:
            if regex.match(model_id):
                return self.llm_config[regex.pattern]

        return None

    def _get_bedrock_models(self, config_model_id_regexs: List[re.Pattern]):
        """Get list of Bedrock models available in the account."""

        start_time = time.time()
        self.logger.info("Retrieving Bedrock models in...")
        models = []
        for bedrock_config in self.bedrock_config:
            region = bedrock_config.parameters.region.value
            endpoint_url = bedrock_config.parameters.endpoint_url
            iam_config = bedrock_config.parameters.iam

            session = get_boto_session(iam_config, region)

            try:
                bedrock_client = session.client(
                    "bedrock", region, endpoint_url=endpoint_url
                )
                foundation_models = bedrock_client.list_foundation_models(
                    byOutputModality="TEXT"
                )["modelSummaries"]

                def sort_list_by_string(matching_str = "", model_list = []):
                    for i, model in enumerate(model_list):
                        if(matching_str in model["modelId"]):
                            model_list = [model_list[i]] + model_list[:i] + model_list[i+1:]
                    return model_list
                
                # surface anthropic models first, then ai21, then others
                foundation_models = sort_list_by_string("ai21", foundation_models)
                foundation_models = sort_list_by_string("anthropic", foundation_models)

                # check the models in config file and apply only if config available
                # also checking only for ON_DEMAND modelds, filtering FINE_TUNNING and PROVISIONED out
                for fm in foundation_models:
                    llm_config=self.get_llm_config(
                        fm["modelId"], config_model_id_regexs
                    )
                    if not llm_config or fm["inferenceTypesSupported"] != ["ON_DEMAND"] or fm["modelId"] in bedrock_config.parameters.hide_models:
                        continue

                    models += [
                        BedrockModelItem(
                            model_id=fm["modelId"],
                            llm_config=self.get_llm_config(
                                fm["modelId"], config_model_id_regexs
                            ),
                            bedrock_config=bedrock_config.parameters,
                            callbacks=self.callbacks,
                            supports_streaming= ("responseStreamingSupported" in fm) and fm["responseStreamingSupported"]
                        )
                    ]

            except (
                botocore.exceptions.EndpointConnectionError,
                botocore.exceptions.NoCredentialsError,
                botocore.exceptions.ConnectTimeoutError,
            ) as err:
                self.logger.info(
                    "No Amazon Bedrock models retrieved in %s.\n%s", region, err
                )
            except botocore.exceptions.ClientError as err:
                self.logger.error(
                    "There was an error while retrieving models from Amazon Bedrock.\n%s",
                    err,
                )
            except botocore.exceptions.UnknownServiceError as err:
                self.logger.info("Running without Amazon Bedrock.\n%s", err)
        self.logger.info(
            "%s Bedrock models retrieved in %s seconds",
            len(models),
            time.time() - start_time,
        )
        self += models

    def _get_sagemaker_models(self):
        """Get list of SageMaker models available in the account that are part of Genie."""
        start_time = time.time()
        self.logger.info("Retrieving SageMaker models...")

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
                    if "genie:prompt-chat" in tags_dict:
                        chat_prompt_identifier = tags_dict["genie:prompt-chat"]
                    rag_prompt_identifier = "prompts/falcon_instruct_rag.yaml"
                    if "genie:prompt-rag" in tags_dict:
                        rag_prompt_identifier = tags_dict["genie:prompt-rag"]
                    async_endpoint_s3 = None
                    if "genie:async-endpoint-s3" in tags_dict:
                        async_endpoint_s3 = tags_dict["genie:async-endpoint-s3"]

                    models.append(
                        SageMakerModelItem(
                            model_name=friendly_name,
                            endpoint_name=endpoint["EndpointName"],
                            region=region,
                            chat_prompt_identifier=chat_prompt_identifier,
                            rag_prompt_identifier=rag_prompt_identifier,
                            async_endpoint_s3=async_endpoint_s3,
                        )
                    )

        self.logger.info(
            "%s SageMaker models retrieved in %s seconds",
            len(models),
            time.time() - start_time,
        )
        self.logger.info(models)

        self += models

    def bootstrap(self) -> None:
        """Bootstraps the catalog."""
        model_id_regex = list(map(re.compile, self.llm_config.keys()))
        self._get_bedrock_models(model_id_regex)
        self._get_sagemaker_models()
