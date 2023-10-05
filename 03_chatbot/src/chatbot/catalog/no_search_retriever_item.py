""" Module that contains a class that represents No search retriever catalog item. """
from dataclasses import dataclass

from langchain.schema import BaseRetriever

from .retriever_catalog_item import RetrieverCatalogItem
from .catalog import CatalogById
from .model_catalog_item import ModelCatalogItem
from chatbot.llm_app import BaseLLMApp, LLMApp


NO_DOCUMENT_SEARCH = "No document search"


@dataclass
class NoRetrieverItem(RetrieverCatalogItem):
    """
    Class that represents using a LLM without a retriever.
    """

    def __init__(self):
        super().__init__(NO_DOCUMENT_SEARCH)

    def get_instance(self) -> BaseRetriever:
        return None

    def llm_app_factory(
        self, model: ModelCatalogItem, prompt_catalog: CatalogById
    ) -> LLMApp:
        """
        Returns the llm app to use for this retriever.
        """
        llm = model.get_instance()
        chat_prompt = prompt_catalog[model.chat_prompt_identifier].get_instance()

        return BaseLLMApp(prompt=chat_prompt, llm=llm)
