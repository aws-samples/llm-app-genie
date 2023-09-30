""" An LLM app represents the logic to interact with a LLM."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import final

import pandas as pd
from langchain.callbacks.base import Callbacks
from langchain.chains import ConversationalRetrievalChain, ConversationChain
from langchain.chains.base import Chain
from langchain.llms.base import LLM
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import BasePromptTemplate
from langchain.schema import BaseChatMessageHistory, BaseMemory, BaseRetriever

GLOBAL_LOGGER_NAME = "Genie"


@dataclass
class LLMApp(ABC):
    """Base class to interact with an LLM."""

    prompt: BasePromptTemplate
    """ The prompt template to use when chatting with the LLM."""
    llm: LLM
    """ The LLM this app uses."""

    @abstractmethod
    def get_chain(self, memory: BaseMemory, callbacks: Callbacks = None) -> Chain:
        """Get the langchain chain that this LLMApp uses.

        Args:
            memory: The memory to use for the chain.
            callbacks: The callbacks to use for the chain.

        Returns:
            The chain that the LLMApp class supports.
        """

    @abstractmethod
    def get_input(self, input_text: str):
        """Turns input string into expected JSON for the LLM.
        Args:
            input_text: The input text to use.

        Returns:
            The JSON to use for the LLM.
        """

    def get_output(self, response) -> str:
        """Extracts the text from a response object.
        Args:
            response: The response from the LLM to extract text from.

        Returns:
            The extracted text.
        """
        if "answer" in response:
            text = response["answer"]
        else:
            text = response
        return text

    def run_llm(
        self, query: str, message_history: BaseChatMessageHistory, callbacks=None
    ):
        """Get the answer from the LLM for a query.
        Args:
            query: The query to use.
            message_history: The message history to use.
            callbacks: The callbacks to use.

        Returns:
            The raw respose from the LLM.
        """
        memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            chat_memory=message_history,
            return_messages=True,
            k=3,
            output_key="answer",
        )  # , human_prefix="[|Human|]", ai_prefix="[|AI|]",return_messages=True)
        chain = self.get_chain(memory=memory, callbacks=callbacks)

        response = chain(self.get_input(query))
        return response

    @final
    def generate_response(
        self, prompt: str, message_history: BaseChatMessageHistory, callbacks=None
    ) -> str:
        """Query the LLM and report the text response form hte LLM."""
        response = self.run_llm(
            query=prompt, message_history=message_history, callbacks=callbacks
        )
        return self.get_output(response)


class BaseLLMApp(LLMApp):
    """Conversational interaction with an LLM."""

    def get_chain(self, memory, callbacks=None):
        """See base class."""
        return ConversationChain(
            llm=self.llm,
            memory=memory,
            prompt=self.prompt,
            verbose=True,
            output_key="answer",
            callbacks=callbacks,
        )

    def get_input(self, input_text: str):
        """See base class."""
        return {"input": input_text}


@dataclass
class RAGApp(LLMApp):
    """Retrieval augmented generation interacts with an LLM uses information from a
    knowledge base."""

    condense_question_prompt_template: BasePromptTemplate
    """Prompt template to use when combining past context with new question."""

    retriever: BaseRetriever

    def get_chain(self, memory, callbacks=None):
        """See base class."""
        return ConversationalRetrievalChain.from_llm(
            return_generated_question=True,
            llm=self.llm,
            retriever=self.retriever,
            memory=memory,
            condense_question_prompt=self.condense_question_prompt_template,
            verbose=False,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": self.prompt},
            callbacks=callbacks,
        )

    def get_input(self, input_text: str):
        """See base class."""
        return {"question": input_text}

    def get_output(self, response) -> str:
        """See base class."""
        text = super().get_output(response)
        if "source_documents" in response and len(response["source_documents"]) > 0:
            resources = [
                {**doc.metadata, **{"page_content": doc.page_content}}
                for doc in response["source_documents"]
            ]
            resources_df = pd.DataFrame(resources)
            resources_df = resources_df.drop_duplicates(subset=["title"], keep="first")
            resources_df = resources_df.assign(num=range(1, len(resources_df) + 1))
            resources_df["title_suffix"] = resources_df.apply(
                lambda row: f"<details><summary> </summary> {row['page_content']}</details>",
                axis=1,
            )
            resources_df["reference"] = resources_df.apply(
                lambda row: f"  {row.num}. [{row['title']}]({row['source']})", axis=1
            )
            resources = "\n \n Resources:\n\n" + "\n".join(
                resources_df["reference"].values
            )

            pos = text.find("Unhelpful Answer")
            if pos > 0:
                text = text[:pos]
            text = text + resources
        return text
