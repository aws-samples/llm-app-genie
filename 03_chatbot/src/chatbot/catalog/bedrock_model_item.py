import boto3
from langchain.llms.base import LLM
from langchain.llms.bedrock import Bedrock

from .model_catalog_item import ModelCatalogItem


class BedrockModelItem(ModelCatalogItem):
    """
    Class that represents a Kendra retriever catalog item.
    """

    region: str
    """ AWS Region """
    endpoint_url: str
    """ Bedrock endpoint URL """
    model_id: str
    """ Model ID """
    model_kwargs: dict
    """ Model kwargs """

    def __init__(
        self,
        model_id,
        endpoint_url,
        chat_prompt_identifier,
        rag_prompt_identifier,
        region=None,
        **model_kwargs,
    ):
        super().__init__(
            f"Bedrock - {model_id} - ({region})",
            chat_prompt_identifier,
            rag_prompt_identifier,
        )
        self.region = region
        self.endpoint_url = endpoint_url
        self.model_kwargs = model_kwargs
        self.model_id = model_id

    def get_instance(self) -> LLM:
        return Bedrock(
            client=boto3.client("bedrock", self.region, endpoint_url=self.endpoint_url),
            model_id=self.model_id,
            region_name=self.region,
            model_kwargs=self.model_kwargs,
        )
