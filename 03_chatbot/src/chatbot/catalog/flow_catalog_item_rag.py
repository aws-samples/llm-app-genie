""" Module that contains a class that represents a File Upload retriever catalog item. """
from dataclasses import dataclass

from langchain.chains.base import Chain

from .flow_catalog_item import FlowCatalogItem
from .retriever_catalog_item import RetrieverCatalogItem
from .catalog import CatalogById
from .model_catalog_item import ModelCatalogItem
from chatbot.llm_app import BaseLLMApp, LLMApp, RAGApp


RETRIEVAL_AUGMENTED_GENERATION = "Retrival Augmented Generation"


@dataclass
class RagItem(FlowCatalogItem):
    """
    Class that represents using a LLM with a retriever.
    """

    def __init__(self):
        super().__init__(RETRIEVAL_AUGMENTED_GENERATION)

    def enable_file_upload(self) -> bool:
        return False

    def enable_retriever(self) -> bool:
        return True

    def get_instance(self) -> Chain:
        return None

    def llm_app_factory(
        self, model: ModelCatalogItem, retriever: RetrieverCatalogItem, prompt_catalog: CatalogById
    ) -> LLMApp:
        """
        Returns the llm app to use for this retriever.
        """
        rag_prompt = prompt_catalog[model.rag_prompt_identifier].get_instance()
        llm = model.get_instance()
        condense_question_prompt = prompt_catalog[
            "prompts/condense_question.yaml"
        ].get_instance()

        retriever = retriever.get_instance()

        return RAGApp(
            prompt=rag_prompt,
            llm=llm,
            condense_question_prompt_template=condense_question_prompt,
            retriever=retriever,
        )
