from typing import Optional

import boto3
from chatbot.config import AmazonBedrockParameters, LLMConfig, LLMConfigParameters
from chatbot.helpers import get_boto_session
from langchain.llms.base import LLM
#from langchain.llms.bedrock import Bedrock
from chatbot.helpers import Bedrock

from .model_catalog_item import ModelCatalogItem


class BedrockModelItem(ModelCatalogItem):
    """
    Class that represents a Kendra retriever catalog item.
    """

    config: AmazonBedrockParameters
    """Amazon Bedrock configuration"""
    model_id: str
    """ Model ID """
    display_model_name: str
    """ Model Name to be displayed in the frontend"""
    model_provider: str
    """ Model provider.
     At the moment, this value is within the following set:
    [''ai21', 'stability, 'anthropic', 'cohere', 'amazon']"""
    model_kwargs: dict
    """ Model kwargs """

    llm_config: LLMConfig

    def __init__(
        self,
        model_id,
        bedrock_config: AmazonBedrockParameters,
        llm_config: Optional[LLMConfig],
        supports_streaming: bool = False,
        callbacks = [],
        **model_kwargs,
    ):
        if llm_config is None:
            llm_config = LLMConfig(LLMConfigParameters())
        if llm_config.parameters.chat_prompt is None:
            llm_config.parameters.chat_prompt = "prompts/default_chat.yaml"
        if llm_config.parameters.rag_prompt is None:
            llm_config.parameters.rag_prompt = "prompts/default_rag.yaml"

        self.llm_config = llm_config
        self.config = bedrock_config
        self.model_kwargs = model_kwargs
        self.model_id = model_id
        self.model_provider = model_id.split(".")[0]
        
        self._set_default_model_kwargs()
        self._set_default_display_model_name()

        self.callbacks = callbacks
        super().__init__(
            self.display_model_name,
            chat_prompt_identifier=llm_config.parameters.chat_prompt,
            rag_prompt_identifier=llm_config.parameters.rag_prompt,
            supports_streaming=supports_streaming,
            streaming_on=supports_streaming
        )

    def get_instance(self) -> LLM:
        region = self.config.region.value
        endpoint_url = self.config.endpoint_url

        iam_config = self.config.iam

        session = get_boto_session(iam_config, region)

        return Bedrock(
            client=session.client("bedrock-runtime", region, endpoint_url=endpoint_url),
            model_id=self.model_id,
            # region_name=region,
            model_kwargs=self.model_kwargs,
            streaming=self.supports_streaming and self.streaming_on,
            callbacks=self.callbacks,
        )

    def _set_default_model_kwargs(self):
        if not self.model_kwargs:
            llm_config = self.llm_config.parameters
            if self.model_provider == "anthropic":  # Anthropic model
                self.model_kwargs = {  # anthropic
                    "max_tokens_to_sample": llm_config.max_token_count or 512,
                    "temperature": llm_config.temperature or 0,
                    "top_k": 250,
                    "top_p": llm_config.top_p or 1,
                    "stop_sequences": llm_config.stop_sequence or ["\n\nHuman:"],
                }

            elif self.model_provider == "ai21":  # AI21
                self.model_kwargs = {  # AI21
                    "maxTokens": llm_config.max_token_count or 512,
                    "temperature": llm_config.temperature or 0,
                    "topP": llm_config.top_p or 0.5,
                    "stopSequences": llm_config.stop_sequence or [],
                    "countPenalty": {"scale": 0},
                    "presencePenalty": {"scale": 0},
                    "frequencyPenalty": {"scale": 0},
                }
            elif self.model_provider == "meta": # Meta
                self.model_kwargs = {  # Meta
                    "max_gen_len": llm_config.max_token_count or 512,
                    "temperature": llm_config.temperature or 0.1,
                    "top_p": llm_config.top_p or 0.9
                }
            else:  # Amazon
                self.model_kwargs = {
                    "maxTokenCount": llm_config.max_token_count or 512,
                    "stopSequences": llm_config.stop_sequence or [],
                    "temperature": llm_config.temperature or 0,
                    "topP": llm_config.top_p or 0.9,
                }

    def _set_default_display_model_name(self):
        if self.model_provider == "amazon":
            self.display_model_name = f"(limited preview) Bedrock - {self.model_id.replace(":",".")} - ({self.config.region.value})"
        else:
            self.display_model_name = f"Bedrock - {self.model_id.replace(":",".")} - ({self.config.region.value})"
