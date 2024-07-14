#!/usr/bin/env python3
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin
import os

from aws_cdk import App, Environment, Tags
from modules.config import config
from stacks.core.core_stack import CoreStack
from stacks.chatbot.chatbot_stack import ChatbotStack
from stacks.deployment_pipeline.deployment_pipeline_stack import DeploymentPipelineStack
from stacks.kendra_datasources.kendra_datasources_stack import KendraDataSourcesStack
from stacks.kendra_index.kendra_index_stack import KendraIndexStack
from stacks.llm_pipeline.llm_pipeline_stack import LLMSageMakerStack
from stacks.opensearch_domain.opensearch_domain_stack import OpenSearchStack
from stacks.opensearch_ingestion_pipeline.opensearch_ingestion_pipeline_stack import (
    OpenSearchIngestionPipelineStack
)
from stacks.opensearch_domain.opensearch_domain_stack import OpenSearchStack
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

# MM let me check it later
deployment_pipeline = DeploymentPipelineStack(app, "DeploymentPipelineStack", env=env)

## Core Stack
core_stack = CoreStack(app, "CoreStack", env=env)

## Basic Infrastructure
## MM check the S3 bucket naming, same as above
llm_pipeline = LLMSageMakerStack(app, "LlmPipelineStack", env=env)
index_stack = KendraIndexStack(app, "KendraIndexStack", env=env, core=core_stack)

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

# ## Chatbot
# ## Move all VPCs to corestack and check for a existing VPC implementation
# chatbot_vpc_cidr_block = "10.0.0.0/16"

# chatbot_vpc = ChatbotVPCStack(
#     app,
#     "ChatBotVPCStack",
#     env=env,
#     cidr_range=chatbot_vpc_cidr_block,
# )

chatbot = ChatbotStack(app, "ChatBotStack", env=env, core=core_stack)
chatbot.add_dependency(core_stack)
# chatbot.add_dependency(chatbot_vpc)

## OpenSearch
## MM:: let's use 1 VPC for the moment
# opensearch_vpc_cidr_block = "10.4.0.0/16"
# opensearch_vpc_stack = OpenSearchPrivateVPCStack(
#     app,
#     "OpenSearchPrivateVpc",
#     env=env,
#     cidr_range=opensearch_vpc_cidr_block,
# )

opensearch_stack_private = OpenSearchStack(
    # app, "PrivateOpenSearchDomainStack", env=env, vpc_output=opensearch_vpc_stack.output
    app, "PrivateOpenSearchDomainStack", env=env, core=core_stack
)

# opensearch_stack_private.add_dependency(opensearch_vpc_stack)


opensearch_vpc_endpoint = OpenSearchVPCEndpointStack(
    app,
    "OpenSearchVPCEndpointStack",
    env=env,
    opensearch_domain=opensearch_stack_private.output.domain,
    consumer_target_vpc=core_stack.vpc,
    consumer_security_group=core_stack.chatbot_security_group
)

opensearch_vpc_endpoint.add_dependency(opensearch_stack_private)
# opensearch_vpc_endpoint.add_dependency(opensearch_vpc_stack)
opensearch_vpc_endpoint.add_dependency(chatbot)




ingestion_pipeline_private = OpenSearchIngestionPipelineStack(
    app,
    "PrivateOpenSearchIngestionPipelineStack",
    env=env,
    core=core_stack,
    opensearch_domain_vpc=opensearch_stack_private.output.vpc_endpoint_output
)





# Add dependecy between OpenSearch and ingestion pipeline
ingestion_pipeline_private.add_dependency(opensearch_stack_private)


# Deprecated. Keep for legacy.
# required to run in non-VPC mode, there should be a better way to do it
core_stack.vpc = None
opensearch_stack = OpenSearchStack(
    app,
    "OpenSearchDomainStack",
    env=env,
    core=core_stack
)


ingestion_pipeline = OpenSearchIngestionPipelineStack(
    app,
    "OpenSearchIngestionPipelineStack",
    core=core_stack,
    env=env
)





# Add dependecy between OpenSearch and ingestion pipeline
ingestion_pipeline.add_dependency(opensearch_stack)



app.synth()
