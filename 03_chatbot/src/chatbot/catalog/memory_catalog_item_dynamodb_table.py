""" from.Module that contains a class that represents a OpenSearch retriever catalog item. """
from dataclasses import dataclass

from langchain.memory.chat_message_histories import DynamoDBChatMessageHistory
from langchain.schema import BaseChatMessageHistory

from .memory_catalog_item import MemoryCatalogItem


@dataclass
class DynamoDBTableMemoryItem(MemoryCatalogItem):
    """Class that represents a Amazon DynamoDB table memory catalog item."""

    table_name: str
    """ DynamoDB table name """

    def __init__(self, table_name):
        super().__init__(f"Memory table: {table_name}")
        self.table_name = table_name

    def get_instance(self, session_id) -> BaseChatMessageHistory:
        return DynamoDBChatMessageHistory(
            table_name=self.table_name, session_id=session_id
        )
