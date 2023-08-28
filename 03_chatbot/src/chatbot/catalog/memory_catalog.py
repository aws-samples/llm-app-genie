""" Module that contains catalog for chat history memory. """
import logging
import sys
import time
from dataclasses import dataclass
from typing import List

import boto3
from chatbot.helpers import get_current_account_id

from .catalog import Catalog
from .dynamodb_table_memory_item import DynamoDBTableMemoryItem


@dataclass
class MemoryCatalog(Catalog):
    """Class for chat history memory catalog."""

    regions: List[str]

    def __init__(self, regions: list) -> None:
        # Regions are initialized before the superclass initialization because
        # the superclass initialization will call the _bootstrap method which
        # requires the regions to be initialized
        self.regions = regions
        super().__init__()

    def _get_dynamodb_memory_table(self, account):
        """Get Amazon DynamoDB table available in the account that is part of Gena."""
        start_time = time.time()
        logging.info("Retrieving DynamoDB memory table...")

        memory_tables = []

        for region in self.regions:
            dynamodb_client = boto3.client("dynamodb", region)

            paginator = dynamodb_client.get_paginator("list_tables")
            tables = paginator.paginate().build_full_result()["TableNames"]

            table_name_to_arn = (
                lambda table_name, region: f"arn:aws:dynamodb:{region}:{account}:table/{table_name}"
            )
            genaix_dynamodb_tag_filter = lambda tag: tag["Key"] == "gena:memory-table"
            for table_name in tables:
                table_arn = table_name_to_arn(table_name, region=region)
                tags_paginator = dynamodb_client.get_paginator("list_tags_of_resource")
                tags = tags_paginator.paginate(
                    ResourceArn=table_arn
                ).build_full_result()["Tags"]
                genaix_tags = list(filter(genaix_dynamodb_tag_filter, tags))
                if len(genaix_tags) > 0:
                    memory_tables.append(DynamoDBTableMemoryItem(table_name=table_name))

        logging.info(
            "%s DynamoDB tables retrieved in %s seconds",
            len(memory_tables),
            time.time() - start_time,
        )
        logging.info(memory_tables)
        if len(memory_tables) > 0:
            logging.info(
                "Using first DynamoDB table %s to store chat history",
                str(memory_tables[0]),
            )
            self.append(memory_tables[0])

    def _bootstrap(self) -> None:
        """Bootstraps the catalog."""
        account = get_current_account_id()

        self._get_dynamodb_memory_table(account)
