from aws_cdk import aws_codecommit as codecommit
from aws_cdk import pipelines
from constructs import Construct
from modules.stack import GenAiStack

stack = {
    "description": "CodeCommit repository to store the chatbot code.",
    "tags": {},
}


class ChatbotCodeCommitRepoStack(GenAiStack):
    @property
    def code_pipeline_source(self) -> pipelines.FileSetLocation:
        return self.__code_pipeline_source

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        # The code that defines your stack goes here

        repository = codecommit.Repository(
            self, "ChatbotRepository", repository_name="aws-gen-ai-alps-mirror"
        )

        self.__code_pipeline_source = pipelines.CodePipelineSource.code_commit(
            repository, "main"
        )
