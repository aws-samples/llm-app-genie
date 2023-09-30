""" Abstract base class that represents a catalog item. """
from dataclasses import dataclass

from langchain.llms.base import LLM

from .catalog_item import CatalogItem


@dataclass
class ModelCatalogItem(CatalogItem[LLM]):
    """Abstract base class that represents a catalog item."""

    chat_prompt_identifier: str
    """ Identifies which prompt to use when chatting with the model. """

    rag_prompt_identifier: str
    """ Identifies which prompt to use with the model when using document retrieval. """
