""" Module that contains an abstract base class that represents an agent chain item.
"""
from dataclasses import dataclass
from langchain.tools import BaseTool
from .agent_chain_catalog_item import AgentChainCatalogItem

AGENT_CHAIN_SQL_GENERATOR_NAME = "SQL query generator"


@dataclass
class SqlGeneratorAgentChainItem(AgentChainCatalogItem):
    """Abstract base class that represents an agent chain for generating SQL."""

    def __init__(self):
        super().__init__(AGENT_CHAIN_SQL_GENERATOR_NAME)

    def get_prompt_path(self) -> str:
        return 'prompts/anthropic_claude_agent_sql.yaml'

    def get_instance(self) -> BaseTool:        
        return None
