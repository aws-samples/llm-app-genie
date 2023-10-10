""" Module that contains catalog for chat history memory. """
import logging
import sys
import time
from dataclasses import dataclass
from logging import Logger, getLogger
from typing import List

import boto3

from .catalog import Catalog
from .memory_catalog_item_dynamodb_table import DynamoDBTableMemoryItem


@dataclass
class MemoryCatalog(Catalog):
    """Class for chat history memory catalog."""

    regions: List[str]

    account_id: str

    logger: Logger

    def __init__(
        self,
        account_id: str,
        regions: list,
        logger: Logger = getLogger("MemoryCatalogLogger"),
    ) -> None:
        self.regions = regions
        self.account_id = account_id
        self.logger = logger
        super().__init__()

    def _get_dynamodb_memory_table(self, account):
        """Get Amazon DynamoDB table available in the account that is part of Genie."""
        start_time = time.time()
        self.logger.info("Retrieving DynamoDB memory table...")

        memory_tables = []

        for region in self.regions:
            dynamodb_client = boto3.client("dynamodb", region)

            paginator = dynamodb_client.get_paginator("list_tables")
            tables = paginator.paginate().build_full_result()["TableNames"]

            table_name_to_arn = (
                lambda table_name, region: f"arn:aws:dynamodb:{region}:{account}:table/{table_name}"
            )
            genaix_dynamodb_tag_filter = lambda tag: tag["Key"] == "genie:memory-table"
            for table_name in tables:
                table_arn = table_name_to_arn(table_name, region=region)
                tags_paginator = dynamodb_client.get_paginator("list_tags_of_resource")
                tags = tags_paginator.paginate(
                    ResourceArn=table_arn
                ).build_full_result()["Tags"]
                genaix_tags = list(filter(genaix_dynamodb_tag_filter, tags))
                if len(genaix_tags) > 0:
                    memory_tables.append(DynamoDBTableMemoryItem(table_name=table_name))

        self.logger.info(
            "%s DynamoDB tables retrieved in %s seconds",
            len(memory_tables),
            time.time() - start_time,
        )
        self.logger.info(memory_tables)
        if len(memory_tables) > 0:
            self.logger.info(
                "Using first DynamoDB table %s to store chat history",
                str(memory_tables[0]),
            )
            self.append(memory_tables[0])

    def bootstrap(self) -> None:
        """Bootstraps the catalog."""

        self._get_dynamodb_memory_table(self.account_id)
