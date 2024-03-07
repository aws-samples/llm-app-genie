#!/usr/bin/env python3
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin
import os

from aws_cdk import App, Environment, Tags
from modules.config import config
from stacks.chatbot.chatbot_stack import ChatbotStack
from stacks.chatbot.chatbot_vpc_stack import ChatbotVPCStack
from stacks.deployment_pipeline.deployment_pipeline_stack import DeploymentPipelineStack
from stacks.kendra_datasources.kendra_datasources_stack import KendraDataSourcesStack
from stacks.kendra_index.kendra_index_stack import KendraIndexStack
from stacks.llm_pipeline.llm_pipeline_stack import LLMSageMakerStack
from stacks.opensearch_domain.opensearch_domain_stack import OpenSearchStack
from stacks.opensearch_ingestion_pipeline.opensearch_ingestion_pipeline_stack import (
    OpenSearchIngestionPipelineStack
)
from stacks.opensearch_domain.opensearch_domain_stack import OpenSearchStack
from stacks.opensearch_domain.opensearch_private_vpc_stack import (
    OpenSearchPrivateVPCStack,
)
from stacks.opensearch_domain.opensearch_vpc_endpoint_stack import (
    OpenSearchVPCEndpointStack,
)
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

## Chatbot
chatbot_vpc_cidr_block = "10.0.0.0/16"


chatbot_vpc = ChatbotVPCStack(
    app,
    "ChatBotVPCStack",
    env=env,
    cidr_range=chatbot_vpc_cidr_block,
)
chatbot = ChatbotStack(app, "ChatBotStack", env=env, vpc=chatbot_vpc.vpc)
chatbot.add_dependency(chatbot_vpc)



## OpenSearch

opensearch_vpc_cidr_block = "10.4.0.0/16"
opensearch_vpc_stack = OpenSearchPrivateVPCStack(
    app,
    "OpenSearchPrivateVpc",
    env=env,
    cidr_range=opensearch_vpc_cidr_block,
)

opensearch_stack_private = OpenSearchStack(
    app, "PrivateOpenSearchDomainStack", env=env, vpc_output=opensearch_vpc_stack.output
)

opensearch_stack_private.add_dependency(opensearch_vpc_stack)


opensearch_vpc_endpoint = OpenSearchVPCEndpointStack(
    app,
    "OpenSearchVPCEndpointStack",
    env=env,
    opensearch_domain=opensearch_stack_private.output.domain,
    consumer_target_vpc=chatbot_vpc.vpc,
    consumer_security_group=chatbot.chatbot_security_group
)

opensearch_vpc_endpoint.add_dependency(opensearch_stack_private)
opensearch_vpc_endpoint.add_dependency(opensearch_vpc_stack)
opensearch_vpc_endpoint.add_dependency(chatbot)




ingestion_pipeline_private = OpenSearchIngestionPipelineStack(
    app,
    "PrivateOpenSearchIngestionPipelineStack",
    env=env,
    opensearch_domain_vpc=opensearch_stack_private.output.vpc_endpoint_output
)





# Add dependecy between OpenSearch and ingestion pipeline
ingestion_pipeline_private.add_dependency(opensearch_stack_private)


# Deprecated. Keep for legacy.
opensearch_stack = OpenSearchStack(
    app,
    "OpenSearchDomainStack",
    env=env,
)


ingestion_pipeline = OpenSearchIngestionPipelineStack(
    app,
    "OpenSearchIngestionPipelineStack",
    env=env
)





# Add dependecy between OpenSearch and ingestion pipeline
ingestion_pipeline.add_dependency(opensearch_stack)



app.synth()
