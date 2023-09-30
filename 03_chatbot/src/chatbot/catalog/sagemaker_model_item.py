""" Module that contains an abstract base class that represents a Kendra retriever catalog item.
"""
import json
import re
from typing import List

from langchain import SagemakerEndpoint
from langchain.llms.base import LLM
from langchain.llms.sagemaker_endpoint import LLMContentHandler

from .model_catalog_item import ModelCatalogItem
from chatbot.helpers.sagemaker_async_endpoint import SagemakerAsyncEndpoint


class SageMakerModelItem(ModelCatalogItem):
    """Class that represents a Kendra retriever catalog item.

    Args:
        model_name: Human friendly name for the model
        endpoint_name: SageMaker endpoint name of the running model
        chat_prompt_identifier: Amazon S3 URI, local path, or LangChainHub path that stores langchain prompt template to use when chatting with the model. Default: "prompts/falcon_chat.yaml"
        rag_prompt_identifier: Amazon S3 URI, local path, or LangChainHub path that stores langchain prompt template to use when using document retrieval. Default: "prompts/falcon_instruct_rag.yaml"
        region: AWS region where the model is running. Default: us-east-1
        model_kwargs: Keyword arguments to pass to the model during inference.

    Example:
        ```python
        sagemaker_model_item = SageMakerModelItem(
            "falcon-40B-endpoint-name", "Falcon 40B", region="eu-west-1"
        )

        sagemaker_endpoint = sagemaker_model_item.get_instance()
        // use sagemaker_endpoint with langchain
        ```
    """

    region: str
    """ AWS Region """
    endpoint_name: str
    """ SageMaker endpoint name """
    model_name: str
    """ SageMaker model name """
    async_endpoint_s3: str | None
    """S3 bucket used by the Asynchronous Sagemaker Endpoint"""
    model_kwargs: dict
    """ SageMaker model kwargs """

    def __init__(
        self,
        model_name: str,
        endpoint_name: str,
        chat_prompt_identifier: str = "prompts/falcon_chat.yaml",
        rag_prompt_identifier: str = "prompts/falcon_instruct_rag.yaml",
        region: str = "us-east-1",
        async_endpoint_s3: str | None = None,
        **model_kwargs,
    ):
        super().__init__(
            f"SageMaker - {model_name}", chat_prompt_identifier, rag_prompt_identifier
        )
        self.region = region
        self.endpoint_name = endpoint_name
        self.model_name = model_name
        self.async_endpoint_s3 = async_endpoint_s3
        self.model_kwargs = model_kwargs

    class ContentHandler(LLMContentHandler):
        content_type = "application/json"
        accepts = "application/json"

        stop_words: List[str]

        def __init__(self, stop_words=[]) -> None:
            super().__init__()
            self.stop_words = stop_words

        def transform_input(self, prompt, model_kwargs):
            # max_new_tokens for Falcon = 2048 - 1900 = 148
            # TODO
            input_str = json.dumps(
                {
                    "inputs": prompt,
                    "parameters": {
                        "do_sample": False,
                        "repetition_penalty": 1.1,
                        "return_full_text": False,
                        "max_new_tokens": 148,
                        "stop": self.stop_words,
                    },
                }
            )
            return input_str.encode("utf-8")

        def transform_output(self, output):
            response_json = json.loads(output.read().decode("utf-8"))
            generated_text = response_json[0]["generated_text"]
            for stop_word in self.stop_words:
                pattern = re.escape(stop_word)
                generated_text = re.sub(pattern, "", generated_text)
            return generated_text

    content_handler = ContentHandler(
        stop_words=["[|Human|]", "<|endoftext|>", "[|AI|]", "Best regards"]
    )

    def get_instance(self) -> LLM:
        if self.async_endpoint_s3 is None:
            llm_sagemaker = SagemakerEndpoint(
                endpoint_name=self.endpoint_name,
                region_name=self.region,
                content_handler=self.content_handler,
            )
        else:
            inputs = (self.async_endpoint_s3).replace("s3://", "").split("/", 1)
            input_bucket, input_prefix = inputs[0], inputs[1]
            llm_sagemaker = SagemakerAsyncEndpoint(
                    endpoint_name=self.endpoint_name,
                    region_name=self.region,
                    content_handler=self.content_handler,
                    input_bucket=input_bucket,
                    input_prefix=input_prefix
            )

        return llm_sagemaker
