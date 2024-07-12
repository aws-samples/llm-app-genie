""" Module that contains a class that represents a OpenSearch retriever catalog item. """
from dataclasses import dataclass
from typing import List

from chatbot.open_search import OpenSearchIndexRetriever
from langchain.schema import BaseRetriever

from .retriever_catalog_item import RetrieverCatalogItem
from typing import Any, List, Tuple, Union
import streamlit as st

@dataclass
class OpenSearchRetrieverItem(RetrieverCatalogItem):
    """Class that represents a Amazon OpenSearch retriever catalog item."""

    region: str
    """ AWS Region """

    rag_config: dict
    """ Global RAG config (Character Limit, Number of documents to retrieve, etc.) """

    embedding_config: dict
    """ SageMaker or Bedrock embedding config """

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
        rag_config,
        embedding_config,
        top_k=3
    ):
        super().__init__(friendly_name)
        self.index_name = ""
        self._data_sources = data_sources
        self._selected_data_sources = []
        self.region = embedding_config["region"]
        self.rag_config = rag_config
        self.embedding_config = embedding_config
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
        if len(self._selected_data_sources) != 1:
            st.error('Please select exactly one data source.')
            return None
        
        index_name = self._selected_data_sources[0][0]

        retriever = OpenSearchIndexRetriever(
            index_name, rag_config=self.rag_config, embedding_config=self.embedding_config, k=self.top_k
        )
        return retriever
