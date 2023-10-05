""" Module that contains a class that represents a File Upload retriever catalog item. """
from dataclasses import dataclass

from langchain.schema import BaseRetriever

from .retriever_catalog_item import RetrieverCatalogItem
from .catalog import CatalogById
from .model_catalog_item import ModelCatalogItem
from chatbot.llm_app import BaseLLMApp, LLMApp


UPLOAD_DOCUMENT_SEARCH = "Upload document search"


@dataclass
class DocUploadItem(RetrieverCatalogItem):
    """
    Class that represents using a LLM without a retriever, but using an uploaded document.
    """

    def __init__(self):
        super().__init__(UPLOAD_DOCUMENT_SEARCH)

    def enable_file_upload(self) -> bool:
        return True

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
