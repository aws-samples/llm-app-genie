"""Chain for question-answering against a vector database."""
from __future__ import annotations

import json
import logging
import sys
from typing import List, Tuple

import boto3
from chatbot.helpers.logger import TECHNICAL_LOGGER_NAME
from langchain.schema import BaseRetriever, Document
from langchain.vectorstores import OpenSearchVectorSearch
from opensearchpy import OpenSearch, AWSV4SignerAuth, RequestsHttpConnection

from sagemaker.huggingface.model import HuggingFacePredictor
from sagemaker.session import Session
from chatbot.embeddings import SageMakerEndpointEmbeddings
from langchain.embeddings import BedrockEmbeddings


logger = logging.getLogger(TECHNICAL_LOGGER_NAME)

try:
    from sagemaker.huggingface.model import HuggingFacePredictor
except json.decoder.JSONDecodeError:
    logger.error(
        "Unable to load HuggingFacePredictor. "
        + "Most likely there is a problem connecting to Amazon SageMaker. "
        + "Do you have AWS credentials configured? "
    )
    sys.exit(0)

def get_credentials(secret_id: str, region_name: str) -> str:
    """Retrieve credentials password for given username from AWS SecretsManager.

    Args:
        secret_id: AWS Secrets Manager id to retrieve.
        region_name: AWS region name.

    Returns:
        AWS Secrets Manager password.

    Example:
        ```python
        credentials = get_credentials("username", "us-east-1")
        ```
    """
    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_id)
    secrets_value = json.loads(response["SecretString"])
    return secrets_value

def get_open_search_index_list(region, domain, os_http_auth = None):
    # Currently supports only OpenSearch serverless
    if not os_http_auth:
        credentials = boto3.Session().get_credentials()
        os_http_auth = AWSV4SignerAuth(credentials, region, 'aoss')

    # client = boto3.client("opensearch", region)
    client = OpenSearch(
        hosts=[{"host": domain["Endpoint"].replace("https://", ""), "port": 443}],
        http_auth=os_http_auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout = 300
    )

    response = client.cat.indices(format="json")

    contains_documents = lambda item: 'docs.count' not in item or item['docs.count'] != '0'

    is_not_hidden = lambda item: not item["index"].startswith(".")

    is_not_system_index = lambda item: item['rep'] in ("1", '')



    # filtering for non system indices only
    indexes = [item for item in response if is_not_system_index and is_not_hidden and contains_documents]
    return indexes

    
class OpenSearchIndexRetriever(BaseRetriever):
    """Retriever to search Amazon OpenSearch.

    Args:
        index_name: OpenSearch index name.
        rag_config: RAG config (number of Documents and number of Characters to retrieve).
        embeddings_config: Embeding enpoing and configuration.
        k: Number of documents to query for. Default: 3

    Example:
        ```python

        embeddings_predictor = HuggingFacePredictor(
            endpoint_name=embeddings_endpoint_name, sagemaker_session=session
        )

        endpoint = "https://<OPEN_SEARCH_DCOMAIN_NAME>.<AWS_REGION>.es.amazonaws.com"
        index_name = "exampleindex"

        opensearchIndexRetriever = OpenSearchIndexRetriever(
            index_name, endpoint, http_auth=os_http_auth, embeddings_predictor=predictor
        )
        ```
    """

    max_character_limit: int

    k: int
    opensearchvectorsearch: OpenSearchVectorSearch
    """ Vector search for OpenSearch. """

    def __init__(
        self,
        index_name: str,
        rag_config,
        embedding_config,         
        k: int = 3, # gets value from slider now
    ):
        if index_name in embedding_config and "rag" in embedding_config[index_name]:
            rag_config = embedding_config[index_name]["rag"]

        # Currently supports only OpenSearch serverless
        # couldn't do it on upper level due to streamlit issue (deepcopy)
        if not embedding_config["http_auth"]:
            credentials = boto3.Session().get_credentials()
            embedding_config["http_auth"] = AWSV4SignerAuth(credentials, embedding_config["region"], 'aoss')

        if  index_name in embedding_config and "embedding" in embedding_config[index_name]:
            embedding_type = embedding_config[index_name]["embedding"]["type"]
            model = embedding_config[index_name]["embedding"]["model"]
        else:
            embedding_type = "Sagemaker"
            model = embedding_config["default_embadding_name"]

        if embedding_type == "Sagemaker":
            boto3_session = boto3.Session(region_name=embedding_config["region"])
            session = Session(boto3_session)
            # replace default endpoint
            predictor = HuggingFacePredictor(
                endpoint_name=model, sagemaker_session=session
            )

            embedding_function = SageMakerEndpointEmbeddings(
                embeddings_predictor=predictor
            )
        elif embedding_type == "Bedrock":
            bedrock_client = boto3.client("bedrock-runtime", region_name=embedding_config["bedrock_region"])
            embedding_function = BedrockEmbeddings(
                client=bedrock_client,
                model_id=model)
        else:
            raise Exception("Embedding type not supported")

        
        opensearchvectorsearch = OpenSearchVectorSearch(
            index_name=index_name,
            embedding_function=embedding_function,
            opensearch_url=embedding_config["endpoint"],
            http_auth=embedding_config["http_auth"],
            timeout = 300,
            connection_class = RequestsHttpConnection,
            use_ssl=True,
            verify_certs=True
        )
        super().__init__(
            k=k,
            max_character_limit=rag_config["maxCharacterLimit"],
            opensearchvectorsearch=opensearchvectorsearch,
        )

    def get_relevant_documents(self, query: str) -> List[Document]:
        """Run search on OpenSearch index and get top k documents.

        Args:
            query: Query string.

        Returns:
            list of documents from this OpenSearch index that relate to the query.
        """
        docs = self.opensearchvectorsearch.similarity_search(query, k=self.k)
        # limit to max character limit
        for doc in docs:
            doc.page_content = doc.page_content[
                : int(min(self.max_character_limit, len(doc.page_content)))
            ]
        return docs

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """See base class."""
        return await super().aget_relevant_documents(query)
