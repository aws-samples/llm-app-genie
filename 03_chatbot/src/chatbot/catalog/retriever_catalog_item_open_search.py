""" Module that contains a class that represents a OpenSearch retriever catalog item. """
from dataclasses import dataclass
from typing import List

import boto3
from babel import Locale
from chatbot.open_search import OpenSearchIndexRetriever, get_credentials
from langchain.schema import BaseRetriever
from sagemaker.huggingface.model import HuggingFacePredictor
from sagemaker.session import Session

from .retriever_catalog_item import RetrieverCatalogItem
from typing import Any, List, Tuple, Union
import streamlit as st

@dataclass
class OpenSearchRetrieverItem(RetrieverCatalogItem):
    """Class that represents a Amazon OpenSearch retriever catalog item."""

    region: str
    """ AWS Region """

    endpoint: str
    """ URL of OpenSearch index """

    embedding_endpoint_name: str
    """ SageMaker embedding endpoint """

    os_http_auth: str
    """ Secret that stores user and password to connect to OpenSearch index """

    _data_sources: Any
    """ OpenSearch indexes in this domain """

    _selected_data_sources: List[Tuple[str, Any]]
    """ OpenSearch indexes that are selected. """

    index_name: str
    """ Selected OpenSearch Index Name """

    def __init__(
        self,
        friendly_name,
        data_sources,
        endpoint,
        embedding_endpoint_name: str,
        os_http_auth,
        region=None,
        top_k=3
    ):
        super().__init__(friendly_name)
        self.index_name = ""
        self._data_sources = data_sources
        self._selected_data_sources = []
        self.region = region
        self.embedding_endpoint_name = embedding_endpoint_name
        self.os_http_auth = os_http_auth
        self.endpoint = endpoint
        self.top_k = top_k

    @property
    def available_filter_options(self) -> Union[List[Tuple[str, Any]], None]:
        return [(data_src["index"], data_src) for data_src in self._data_sources]

    @property
    def current_filter(self) -> List[str]:
        return [
            (data_src["index"], data_src) for data_src in self._selected_data_sources
        ]

    @current_filter.setter
    def current_filter(self, value: List[Tuple[str, Any]]):
        selected_and_part_of_index = list(
            filter(lambda x: x[1] in self._data_sources, value)
        )
        self._selected_data_sources = selected_and_part_of_index


    def get_instance(self) -> BaseRetriever:
        embeddings_endpoint_name = self.embedding_endpoint_name
        
        os_http_auth = self.os_http_auth
        endpoint = self.endpoint

        if len(self._selected_data_sources) != 1:
            st.error('Please select exactly one data source.')
            return None
        
        index_name = self._selected_data_sources[0][0]
        region = self.region
        top_k = self.top_k

        boto3_session = boto3.Session(region_name=region)
        session = Session(boto3_session)
        predictor = HuggingFacePredictor(
            endpoint_name=embeddings_endpoint_name, sagemaker_session=session
        )

        retriever = OpenSearchIndexRetriever(
            index_name, endpoint, http_auth=os_http_auth, embeddings_predictor=predictor, k=top_k
        )
        return retriever
