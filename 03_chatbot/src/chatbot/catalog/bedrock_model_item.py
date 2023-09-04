import boto3
from chatbot.config import AmazonBedrockParameters
from langchain.llms.base import LLM
from langchain.llms.bedrock import Bedrock

from .model_catalog_item import ModelCatalogItem


class BedrockModelItem(ModelCatalogItem):
    """
    Class that represents a Kendra retriever catalog item.
    """

    config: AmazonBedrockParameters
    """Amazon Bedrock configuration"""
    model_id: str
    """ Model ID """
    model_kwargs: dict
    """ Model kwargs """

    def __init__(
        self,
        model_id,
        bedrock_config: AmazonBedrockParameters,
        chat_prompt_identifier,
        rag_prompt_identifier,
        **model_kwargs,
    ):
        super().__init__(
            f"Bedrock - {model_id} - ({bedrock_config.region.value})",
            chat_prompt_identifier,
            rag_prompt_identifier,
        )
        self.config = bedrock_config
        self.model_kwargs = model_kwargs
        self.model_id = model_id

    def get_instance(self) -> LLM:
        region = self.config.region.value
        endpoint_url = self.config.endpoint_url
        profile = self.config.profile

        session = boto3.Session(profile_name=profile)

        return Bedrock(
            client=session.client("bedrock", region, endpoint_url=endpoint_url),
            model_id=self.model_id,
            region_name=region,
            **self.model_kwargs,
        )
