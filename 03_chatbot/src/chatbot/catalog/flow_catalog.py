""" Module that contains a flow catalog.
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
from .flow_catalog_item_simple_chat import SimpleChatFlowItem
from .flow_catalog_item_upload_file import DocUploadItem
from .flow_catalog_item_rag import RagItem
from .flow_catalog_item_agent import AgentsItem

@dataclass
class FlowCatalog(Catalog):
    """Catalog to get flows."""

    regions: List[str]

    account_id: str

    logger: Logger

    def __init__(
        self,
        account_id,
        regions: list,
        logger: Logger = getLogger("FlowCatalogLogger"),
    ) -> None:
        self.regions = regions
        self.account_id = account_id
        self.logger = logger
        super().__init__()

    def _add_simple_chat_flow_option(self) -> None:
        self.append(SimpleChatFlowItem())

    def _add_doc_upload_flow_option(self) -> None:
        self.append(DocUploadItem())
        
    def _add_rag_option(self) -> None:
        self.append(RagItem())

    def _add_agent_option(self) -> None:
        self.append(AgentsItem())
        


    def bootstrap(self) -> None:
        """Bootstraps the catalog."""
        self._add_simple_chat_flow_option()
        self._add_doc_upload_flow_option()
        self._add_rag_option()
        self._add_agent_option()
