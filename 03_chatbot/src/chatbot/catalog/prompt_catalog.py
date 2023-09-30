""" Module that contains catalog for prompts. """
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import boto3
import yaml
from langchain.prompts import BasePromptTemplate
from langchain.prompts import load_prompt as langchain_load_prompt
from langchain.prompts.loading import load_prompt_from_config

from .catalog import CatalogById
from .prompt_catalog_item import PromptCatalogItem

dirname = os.path.dirname(__file__)
basedir = os.path.join(dirname, "../")


@dataclass
class PromptCatalog(CatalogById[PromptCatalogItem]):
    """Class to get and load prompt templates."""

    def _retrieve(self, key: str) -> PromptCatalogItem:
        prompt = self._load_prompt(key)
        return PromptCatalogItem(friendly_name=key, prompt=prompt)

    def _try_load_from_s3(
        self,
        path: Union[str, Path],
    ) -> BasePromptTemplate:
        """Load configuration from S3."""
        S3_URI = re.compile(r"s3://(?P<ref>.+)/(?P<path>.*)")
        s3Client = boto3.client("s3")

        if not isinstance(path, str) or not (match := S3_URI.match(path)):
            return None
        bucket, object_key = match.groups()

        object_path = Path(object_key)

        valid_suffixes = {"json", "yaml"}

        if object_path.suffix[1:] not in valid_suffixes:
            raise ValueError("Unsupported file type.")

        response = s3Client.get_object(Bucket=bucket, Key=object_key)

        content = response["Body"].read()
        if object_path.suffix == ".json":
            config = json.load(content)
        elif object_path.suffix == ".yaml":
            config = yaml.safe_load(content)
        return load_prompt_from_config(config)

    def _load_prompt(self, path: Union[str, Path]) -> BasePromptTemplate:
        """Unified method for loading a prompt from Amazon S3, LangChainHub or local fs."""
        if s3_result := self._try_load_from_s3(path):
            return s3_result
        else:
            path_from_base = os.path.join(basedir, path)
            return langchain_load_prompt(path_from_base)
