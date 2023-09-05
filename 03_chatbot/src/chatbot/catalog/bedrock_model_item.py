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
    model_provider: str
    """ Model provider.
     At the moment, this value is within the following set:
    [''ai21', 'stability, 'anthropic', 'cohere', 'amazon']"""
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
        self.model_provider = model_id.split(".")[0]

        self._set_default_model_kwargs()

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

    def _set_default_model_kwargs(self):
        if not self.model_kwargs:
            if (self.model_provider == 'anthropic'): #Anthropic model
                self.model_kwargs = { #anthropic
                    "max_tokens_to_sample": 512,
                    "temperature": 0, 
                    "top_k": 250, 
                    "top_p": 1, 
                    "stop_sequences": ["\n\nHuman:"] 
                }
            
            elif (self.model_provider == 'ai21'): #AI21
                self.model_kwargs = { #AI21
                    "maxTokens": 512, 
                    "temperature": 0, 
                    "topP": 0.5, 
                    "stopSequences": [], 
                    "countPenalty": {"scale": 0 }, 
                    "presencePenalty": {"scale": 0 }, 
                    "frequencyPenalty": {"scale": 0 } 
                }
            
            else: #Amazon
                self.model_kwargs = { 
                    "maxTokenCount": 512, 
                    "stopSequences": [], 
                    "temperature": 0, 
                    "topP": 0.9 
                }
