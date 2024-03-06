""" Module that contains a retriever catalog.
"""
import logging
import time
from dataclasses import dataclass
from logging import Logger, getLogger
from operator import itemgetter
from typing import List

import boto3
import botocore

from .catalog import FRIENDLY_NAME_TAG, Catalog
from .retriever_catalog_item_kendra import KendraRetrieverItem
from .retriever_catalog_item_open_search import OpenSearchRetrieverItem
from ..fin_analyzer.retriever_catalog_item_fin_analyzer import FinAnalyzerRetrieverItem
from chatbot.open_search import get_credentials, get_open_search_index_list
from chatbot.config import AppConfig
import opensearchpy

@dataclass
class RetrieverCatalog(Catalog):
    """Catalog to get document retrievers."""

    regions: List[str]

    account_id: str

    logger: Logger

    app_config: AppConfig



    def __init__(
        self,
        account_id,
        regions: list,
        app_config: AppConfig,
        logger: Logger = getLogger("RetrieverCatalogLogger"),
    ) -> None:
        self.regions = regions
        self.account_id = account_id
        self.logger = logger
        self.app_config = app_config
        super().__init__()

    def _get_kendra_indices(self, account):
        """Get list of kendra indices that contain a "friendly-name" tag."""

        start_time = time.time()
        self.logger.info("Retrieving Kendra indices...")
        index_summary_items = []

        for region in self.regions:
            kendra_client = boto3.client("kendra", region)
            response = kendra_client.list_indices()
            index_summary_items = response["IndexConfigurationSummaryItems"]

            while "NextToken" in response:
                next_token = response.get("NextToken")
                response = kendra_client.list_indices(NextToken=next_token)
                index_summary_items += response["IndexConfigurationSummaryItems"]

            # Filter out active indices
            for index in filter(lambda x: x["Status"] == "ACTIVE", index_summary_items):
                index_id = index["Id"]

                kendra_index_arn = f"arn:aws:kendra:{region}:{account}:index/{index_id}"
                tags = kendra_client.list_tags_for_resource(
                    ResourceARN=kendra_index_arn
                )["Tags"]
                tags_dict = {tag["Key"]: tag["Value"] for tag in tags}
                if FRIENDLY_NAME_TAG in tags_dict:
                    response = kendra_client.list_data_sources(IndexId=index_id)
                    data_sources = response["SummaryItems"]

                    while "NextToken" in response:
                        next_token = response.get("NextToken")
                        response = kendra_client.list_data_sources(
                            IndexId=index_id, NextToken=next_token
                        )
                        data_sources += response["SummaryItems"]

                    active_data_sources = list(
                        filter(lambda x: x["Status"] == "ACTIVE", data_sources)
                    )
                    if len(active_data_sources) > 0:
                        self.append(
                            KendraRetrieverItem(
                                index_id=index_id,
                                friendly_name=tags_dict[FRIENDLY_NAME_TAG],
                                region=region,
                                data_sources=active_data_sources,
                            )
                        )

        self.logger.info(
            "%s Kendra indices retrieved in %s seconds",
            len(self),
            time.time() - start_time,
        )

    def _get_open_search_indices(self, account):
        """Get list of OpenSearch indices that contain a "friendly-name" tag."""
        start_time = time.time()
        self.logger.info("Retrieving OpenSearch indices...")
        opensearch_indices = []

        for region in self.regions:
            # Get OpenSearch domains
            self.logger.info("OpenSearch region: %s", region)
            open_search_client = boto3.client("opensearch", region)
            try:
                response = open_search_client.list_domain_names(EngineType="OpenSearch")
            except (
                botocore.exceptions.ClientError,
                botocore.exceptions.ConnectTimeoutError,
            ):
                self.logger.info(
                    f"Not using OpenSearch in region {region}. Cannot connect to OpenSearch to list domains."
                )
                continue
            self.logger.info("OpenSearch response: %s", response)

            domain_names = [
                name_dict["DomainName"] for name_dict in response["DomainNames"]
            ]
            self.logger.info("OpenSearch domain names: %s", domain_names)

            self.logger.info("describe_domains...")
            try:
                response = open_search_client.describe_domains(DomainNames=domain_names)
            except (
                botocore.exceptions.ClientError,
                botocore.exceptions.ConnectTimeoutError,
            ):
                self.logger.info(
                    f"Not using OpenSearch in region {region}. Cannot connect to OpenSearch to describe domains."
                )
                continue
            domains = response["DomainStatusList"]

            sagemaker_client = boto3.client("sagemaker", region)
            secrets_manager_client = boto3.client("secretsmanager", region)

            active_domain_filter = (
                lambda domain: not domain["Processing"] and domain["Created"]
            )
            for domain in filter(active_domain_filter, domains):
                domain_arn = domain["ARN"]
                self.logger.info("domain: %s", domain_arn)
                try:
                    tags = open_search_client.list_tags(ARN=domain_arn)["TagList"]
                except (
                    botocore.exceptions.ClientError,
                    botocore.exceptions.ConnectTimeoutError,
                ):
                    self.logger.info(
                        f"Cannot connect to OpenSearch to list tags for {domain_arn}."
                    )
                    continue
                tags_keys = list(map(itemgetter("Key"), tags))
                
                
                def get_genai_tag_value_by_key(tags, key):
                    if key not in tags_keys:
                        return None
                    return tags[list(map(itemgetter("Key"), tags)).index(key)][
                        "Value"
                    ]

                friendly_name_tag_value = get_genai_tag_value_by_key(
                    tags, FRIENDLY_NAME_TAG
                )
                secrets_tag_value = get_genai_tag_value_by_key(
                    tags, "genie:secrets-id"
                )
                embedding_sagemaker_name = get_genai_tag_value_by_key(
                    tags,
                    "genie:sagemaker-embedding-endpoint-name",
                )

                vpc_endpoint_value = get_genai_tag_value_by_key(
                    tags,
                    "genie:chatbot_vpc_endpoint",
                )

                if (
                    friendly_name_tag_value
                    and secrets_tag_value
                    and embedding_sagemaker_name
                ):
                    
                    try:
                        embedding_endpoint = sagemaker_client.describe_endpoint(
                            EndpointName=embedding_sagemaker_name
                        )
                    except (
                        botocore.exceptions.ClientError,
                        botocore.exceptions.ConnectTimeoutError,
                    ):
                        self.logger.info(
                            f"Cannot connect to embeddings endpoint {embedding_sagemaker_name} on Amazon SageMaker for OpenSearch domain {domain_arn}."
                        )
                        continue

                    if (
                        not embedding_endpoint
                        or "EndpointStatus" not in embedding_endpoint
                        or embedding_endpoint["EndpointStatus"] != "InService"
                    ):
                        self.logger.info(
                            f"Ignoring OpenSearch domain {domain_arn} because embeddings endpoint {embedding_sagemaker_name} on Amazon SageMaker is not in service."
                        )
                        continue

                    try:
                        secret = get_credentials(secrets_tag_value, region)
                        os_http_auth = (secret["user"] or "admin", secret["password"])
                    except (
                        botocore.exceptions.ClientError,
                        botocore.exceptions.ConnectTimeoutError,
                    ):
                        self.logger.info(
                            f"Cannot get credentials for OpenSearch domain from AWS Secrets Manager. Ignoring OpenSearch domain {domain_arn}."
                        )
                        continue
                    
                    try:
                        #vpc_id = self.environment.get_env_variable(ChatbotEnvironmentVariables.Vpc)

                        endpoint = None
                        if vpc_endpoint_value:
                            # get the VPC endpoint for the domain

                            # next_token = None

                            # list_endpoint_response = open_search_client.list_vpc_endpoints_for_domain(
                            #     DomainName=domain["DomainName"],
                            #     NextToken=next_token
                            # )
                            # if 'NextToken' in list_endpoint_response:
                            #     next_token = list_endpoint_response['NextToken']
                            # else: 
                            #     next_token = None
                            # available_vpc_endpoint_ids = [vpc_endpoint['VpcEndpointId']  for vpc_endpoint in list_endpoint_response['VpcEndpointSummaryList'] if vpc_endpoint['VpcEndpointOwner'] == account and vpc_endpoint['Status'] == "ACTIVE"]
                            # describe_vpc_endpoints_response = open_search_client.describe_vpc_endpoints(
                            #     VpcEndpointIds=available_vpc_endpoint_ids
                            # )
                            # vpc_endpoints_in_vpc = [vpc_endpoint for vpc_endpoint in describe_vpc_endpoints_response['VpcEndpoints'] if vpc_endpoint['VpcOptions']['VPCId'] == vpc_id]
                            endpoint = vpc_endpoint_value
                        else:
                            if 'Endpoint' in domain:
                                endpoint=domain['Endpoint']
                            elif 'EndpointV2' in domain:
                                endpoint=domain['EndpointV2']
                            elif 'Endpoints' in domain:
                                endpoint = domain['Endpoints']['vpc']
                            else:
                                self.logger.info(
                                    f"Cannot get endpoint for OpenSearch domain. Ignoring OpenSearch domain {domain_arn}."
                                )
                                continue

                        if endpoint:
                            domain['Endpoint'] = endpoint

                            data_sources = get_open_search_index_list(region, domain, os_http_auth)


                            if data_sources:
                                opensearch_indices.append(
                                    OpenSearchRetrieverItem(
                                        friendly_name=friendly_name_tag_value,
                                        region=region,
                                        data_sources = data_sources,
                                        endpoint=f"https://{endpoint}",
                                        embedding_endpoint_name=embedding_sagemaker_name,
                                        os_http_auth = os_http_auth

                                    )
                                )
                    except (
                        opensearchpy.ImproperlyConfigured,
                        opensearchpy.OpenSearchException
                    ) as e:
                        self.logger.info(
                            f"Cannot connect to OpenSearch domain. Ignoring OpenSearch domain {domain_arn}. {str(e)}"
                        )
                        continue

        self += opensearch_indices
        self.logger.info(
            "%s OpenSearch indices retrieved in %s seconds",
            len(opensearch_indices),
            time.time() - start_time,
        )

    def _get_fin_analyzer_indices(self, account):
        """Get list of FinAnalyzer indices, based on application config (appconfig.json)."""
        
        config = self.app_config.fin_analyzer
        if config is None:
            self.logger.info(
                f"Skipping Finance Analyzer indices due to missing configuration."
            )
            return

        start_time = time.time()
        logging.info("Retrieving FinAnalyzer indices...")

        for region in self.regions:
            self.append(
                FinAnalyzerRetrieverItem(
                    index_id="FinAnalyzer",
                    config=config.parameters,
                    region=region
                )
            )

        logging.info(
            "%s FinAnalyzer indices retrieved in %s seconds",
            len(self),
            time.time() - start_time,
        )

    def bootstrap(self) -> None:
        """Bootstraps the catalog."""
        self._get_kendra_indices(self.account_id)
        self._get_open_search_indices(self.account_id)
        self._get_fin_analyzer_indices(self.account_id)
