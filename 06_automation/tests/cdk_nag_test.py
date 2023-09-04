""" Scan stacks with cdk_nag https://github.com/cdklabs/cdk-nag.

Run `poetry install --with test` to install cdk_nag.

Run cdk_nag with `poetry run python tests/cdk_nag_test.py`.
"""
#!/usr/bin/env python3
import os

from aws_cdk import App, Aspects, Environment, Tags
from cdk_nag import AwsSolutionsChecks
from modules.config import config
from stacks.chatbot.chatbot_cicd_stack import ChatbotCiCdStack
from stacks.chatbot.chatbot_codecommit_repo_stack import ChatbotCodeCommitRepoStack
from stacks.chatbot.chatbot_stack import ChatbotStack
from stacks.kendra_datasources.kendra_datasources_stack import KendraDataSourcesStack
from stacks.kendra_index.kendra_index_stack import KendraIndexStack
from stacks.llm_pipeline.llm_pipeline_stack import LLMSageMakerStack
from stacks.opensearch_domain.opensearch_domain_stack import OpenSearchStack
from stacks.opensearch_ingestion_pipeline.opensearch_ingestion_pipeline_stack import (
    OpenSearchIngestionPipelineStack,
)

# load the details from defaul AWS config
env = Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"]
)

print(
    f"""
+-------------------------------------------------------------------------+
    You are deploying {config["appPrefix"]} solution into:
    {env.account} account in {env.region} region.
+-------------------------------------------------------------------------+
"""
)

app = App()

Aspects.of(app).add(AwsSolutionsChecks(verbose=True))


# ------------------------------------------------------------------------------
# assign global tags to stack
# ------------------------------------------------------------------------------
for key, value in config["globalTags"].items():
    Tags.of(app).add(key, value)

## Basic Infrastructure
llm_pipeline = LLMSageMakerStack(
    app,
    "AiLlmPipelineStack",
    env=env,
)

opensearch_stack = OpenSearchStack(
    app,
    "OpenSearchDomainStack",
    env=env,
)
ingestion_pipeline = OpenSearchIngestionPipelineStack(
    app,
    "OpenSearchIngestionPipelineStack",
    env=env,
)
# Add dependecy between OpenSearch and ingestion pipeline
ingestion_pipeline.add_dependency(opensearch_stack)

index_stack = KendraIndexStack(
    app,
    "KendraIndexStack",
    env=env,
)

datasource_stack = KendraDataSourcesStack(
    app,
    "KendraDataSourcesStack",
    index=index_stack.index,
    env=env,
)

# Add dependency between index and datasource
datasource_stack.add_dependency(index_stack)

## Dev Environment
# SageMakerStudioStack(app, "SageMakerStudioDomainStack", env=env)

## Streamlit chatbot
chatbot = ChatbotStack(app, "ChatBotStack", env=env)

chatbot_code_commit_repo = ChatbotCodeCommitRepoStack(
    app, "ChatBotCodeCommitRepoStack", env=env
)
chatbot_cicd_stack = ChatbotCiCdStack(
    app,
    "ChatBotCiCdStack",
    chatbot_app_stack_source=chatbot_code_commit_repo.code_pipeline_source,
    env=env,
)
chatbot_cicd_stack.add_dependency(chatbot_code_commit_repo)


app.synth()
