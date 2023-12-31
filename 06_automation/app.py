#!/usr/bin/env python3
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin
import os

from aws_cdk import App, Environment, Tags
from modules.config import config
from stacks.chatbot.chatbot_stack import ChatbotStack
from stacks.deployment_pipeline.deployment_pipeline_stack import DeploymentPipelineStack
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

# ------------------------------------------------------------------------------
# assign global tags to stack
# ------------------------------------------------------------------------------
for key, value in config["globalTags"].items():
    Tags.of(app).add(key, value)

deployment_pipeline = DeploymentPipelineStack(app, "DeploymentPipelineStack", env=env)
## Basic Infrastructure
llm_pipeline = LLMSageMakerStack(
    app,
    "LlmPipelineStack",
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
existing_vpc = config.get("existing_vpc_id")
if existing_vpc:
    print(
        f"""
    +-------------------------------------------------------------------------+
        Deploying chatbot into existing VPC {existing_vpc}.
    +-------------------------------------------------------------------------+
    """
    )
chatbot = ChatbotStack(app, "ChatBotStack", env=env, existing_vpc_id=existing_vpc)

app.synth()
