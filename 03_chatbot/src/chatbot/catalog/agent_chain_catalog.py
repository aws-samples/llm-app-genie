""" Module that contains an agent chains catalog.
"""
import logging
import time
from dataclasses import dataclass
from logging import Logger, getLogger
from typing import List

from .catalog import FRIENDLY_NAME_TAG, Catalog
from .agent_chain_catalog_item_financial_analysis import FinancialAnalysisAgentChainItem
from .agent_chain_catalog_item_sql_generator import SqlGeneratorAgentChainItem


@dataclass
class AgentChainCatalog(Catalog):
    """Catalog to get agent chains."""

    regions: List[str]
    logger: Logger

    def __init__(
        self,
        regions: list,
        logger: Logger = getLogger("AgentChainCatalogLogger"),
    ) -> None:
        self.regions = regions
        self.logger = logger
        super().__init__()

    def _get_agent_chain_financial_analysis(self):
        """Get agent chain for financial analysis"""

        start_time = time.time()
        self.logger.info("Retrieving Agent Chain for financial analysis...")

        _var = FinancialAnalysisAgentChainItem()
        self += [_var]

        self.logger.info(
            "%s Financial Analysis Agent Chain retrieved in %s seconds",
            len(self),
            time.time() - start_time,
        )

    def _get_agent_chain_sql_generator(self):
        """Get agent chain for SQL generation"""

        start_time = time.time()
        self.logger.info("Retrieving Agent Chain for SQL generation...")

        _var = SqlGeneratorAgentChainItem()
        self += [_var]

        self.logger.info(
            "%s SQL generation Agent Chain retrieved in %s seconds",
            len(self),
            time.time() - start_time,
        )


    def bootstrap(self) -> None:
        """Bootstraps the catalog."""
        self._get_agent_chain_financial_analysis()
        self._get_agent_chain_sql_generator()
