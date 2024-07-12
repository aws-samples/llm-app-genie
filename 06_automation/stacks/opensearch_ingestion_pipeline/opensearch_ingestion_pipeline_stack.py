# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin
import json
import aws_cdk
from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_secretsmanager as sm
from constructs import Construct
from aws_cdk import aws_ec2 as ec2
from typing import Optional
from modules.config import config, quotas, quotas_client
from modules.stack import GenAiStack
from stacks.opensearch_domain.opensearch_domain_stack import OpenSearchVpcOutput
from ..shared.s3_access_logs_stack import S3AccessLogsStack
from stacks.core.core_stack import CoreStack

import logging

stack = {"description": "OpenSearch Ingestion Pipeline", "tags": {}}
class OpenSearchIngestionPipelineStack(GenAiStack):
    """A root construct which represents a codepipeline CloudFormation stack."""

    def __init__(
            self, 
            scope: Construct, 
            construct_id: str, 
            core: CoreStack,
            opensearch_domain_vpc: Optional[OpenSearchVpcOutput] = None,
            **kwargs
    ) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        response = quotas_client.get_service_quota(
            ServiceCode="sagemaker",
            QuotaCode=quotas[config["sagemaker"]["embeddings_instance_type"]],
        )

        # check for required instance quate in account
        if response["Quota"]["Value"] == 0.0:
            logging.fatal(f"Please adjust your quota for the Embeddings Endpoint for type {config['sagemaker']['embeddings_instance_type']}")
            return
        else:
            print(
                f"You have enough instances quotas for the Embeddings Endpoint of type {config['sagemaker']['embeddings_instance_type']}"
            )

        bucket_name = f"{config['appPrefixLowerCase']}-sagemaker-{self.account}-{self.region}"
        
        ssm.StringParameter(
            scope=self,
            id="SagemakerEmbeddingsInstanceType",
            parameter_name=config['appPrefix'] + "SagemakerEmbeddingsInstanceType",
            string_value=config["sagemaker"]["embeddings_instance_type"],
        )

        ssm.StringParameter(
            scope=self,
            id="HfPredictorEndpointName",
            parameter_name=config['appPrefix'] + "HfPredictorEndpointName",
            string_value=config["sagemaker"]["embeddings_endpoint_name"],
        )

        ssm.StringParameter(
            scope=self,
            id="CrawledFileLocation",
            parameter_name=config['appPrefix'] + "CrawledFileLocation",
            string_value="TO_BE_SET",
        )

        ssm.StringParameter(
            scope=self,
            id="OpenSearchIndexName",
            parameter_name=config['appPrefix'] + "OpenSearchIndexName",
            string_value=config["opensearch"]["index"],
        )

        # get fin_analyzer api secrets
        # TODO: make this check below as well
        if "fin_analyzer" in config and "secret" in config["fin_analyzer"]:  
            fin_analyzer_apis = sm.Secret(
                scope=self,
                id=config["appPrefix"] + "FinAnalyzerAPIs",
                secret_string_value = aws_cdk.SecretValue(json.dumps(config["fin_analyzer"]["secret"]))
            )

        s3_access_logs = S3AccessLogsStack(
            scope=self,
            construct_id="IngestionPipelineBucketAccessLogsBucketStack"
        )

        artifacts_lifecycle_rule = s3.LifecycleRule(
            id="IngestionPipelineBucketLifecycleRule",
            abort_incomplete_multipart_upload_after=Duration.days(1),
            enabled=True,
            expiration=Duration.days(360),
           # expired_object_delete_marker=True,
            transitions=[s3.Transition(
                storage_class=s3.StorageClass.GLACIER,

                transition_after=Duration.days(180),
            )]
        )

        s3_bucket = s3.Bucket(
            self,
            "IngestionPipelineBucket",
            versioned=False,
            bucket_name=bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            server_access_logs_bucket=s3_access_logs.bucket,
            lifecycle_rules=[artifacts_lifecycle_rule]
        )

        repo_embeddings = codecommit.Repository(
            self,
            "SagemakerEmbeddings",
            repository_name=config['appPrefix'] + "SagemakerEmbeddings",
            code=codecommit.Code.from_directory(
                "../00_llm_endpoint_setup/codebuild/embeddings", branch="main"
            ),
        )

        repo_crawler = codecommit.Repository(
            self,
            "CustomCrawler",
            repository_name=config['appPrefix'] + "CustomCrawler",
            code=codecommit.Code.from_directory("../01_crawler", branch="main"),
        )

        repo_ingestion = codecommit.Repository(
            self,
            "Ingestion",
            repository_name=config['appPrefix'] + "Ingestion",
            code=codecommit.Code.from_directory("../02_ingestion", branch="main"),
        )

        build_image = codebuild.LinuxBuildImage.STANDARD_7_0

        secrets_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ssm:GetParameters", "ssm:GetParameter"],
                    resources=[
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter/{config['appPrefix']}HfPredictorEndpointName",
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter/{config['appPrefix']}OpenSearchDomainName",
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter/{config['appPrefix']}OpenSearchEndpoint",
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter/{config['appPrefix']}OpenSearchIndexName",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ssm:GetParameters",
                        "ssm:GetParameter",
                        "ssm:PutParameter",
                    ],
                    resources=[
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter/{config['appPrefix']}CrawledFileLocation"
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["secretsmanager:ListSecrets"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "secretsmanager:GetResourcePolicy",
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret",
                        "secretsmanager:ListSecretVersionIds",
                    ],
                    resources=[
                        f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{config['appPrefix']}OpenSearchCredentials*",
                        # create secret and automate it
                        f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{config['appPrefix']}FinAnalyzerAPIs*"
                    ],
                ),
            ]
        )
        bedrock_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["bedrock:InvokeModel"],
                    resources=["arn:aws:bedrock:*::foundation-model/*"]
                )
            ]
        )

        s3_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:ListObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListBucket",
                        "s3:GetBucketLocation",
                        "s3:GetObjectVersion"
                    ],
                    resources=[
                        f"arn:aws:s3:::{core.data_sources_bucket.bucket_name}",
                        f"arn:aws:s3:::{core.data_sources_bucket.bucket_name}/*"
                    ]
            )
        ])


        iam_role = iam.Role(
            self,
            "CodeBuildRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
                iam.ServicePrincipal("codebuild.amazonaws.com"),
                iam.ServicePrincipal("codepipeline.amazonaws.com"),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonOpenSearchServiceFullAccess"
                ),  # in ingest and create indexes
            ],
            inline_policies={
                "parametersAndSecrets": secrets_policy,
                "BedrockAccess": bedrock_policy,
                "S3Policy": s3_policy
            },
        )

        cdk_deploy = codebuild.PipelineProject(
            self,
            config["appPrefix"] + "SageMakerEmbeddingsEndpoint",
            build_spec=codebuild.BuildSpec.from_asset(
                "../00_llm_endpoint_setup/codebuild/embeddings/buildspec.yml"
            ),
            environment=codebuild.BuildEnvironment(build_image=build_image),
            environment_variables=(
                {
                    "S3_BUCKET": codebuild.BuildEnvironmentVariable(
                        value=f"s3://{bucket_name}"
                    ),
                    "MODEL_EXECUTION_ROLE_ARN": codebuild.BuildEnvironmentVariable(
                        value=iam_role.role_arn
                    ),
                    "INSTANCE_TYPE": codebuild.BuildEnvironmentVariable(
                        value=config["sagemaker"]["embeddings_instance_type"]
                    ),
                    "REGION": codebuild.BuildEnvironmentVariable(value=self.region),
                    "EXPORT_TEMPLATE_NAME": codebuild.BuildEnvironmentVariable(
                        value="exported-template.yml"
                    ),
                    "ARTIFACT_BUCKET": codebuild.BuildEnvironmentVariable(
                        value=f"s3://{s3_bucket.bucket_name}"
                    ),
                    "EXPORT_CONFIG": codebuild.BuildEnvironmentVariable(
                        value="config.json"
                    ),
                    "ENDPOINT_NAME": codebuild.BuildEnvironmentVariable(
                        value=config['appPrefix'] + config["sagemaker"]["embeddings_endpoint_name"]
                    ),
                }
            ),
            description="Deploy SageMaker embeddings endpoint",
            timeout=Duration.minutes(120),
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.DOCKER_LAYER, codebuild.LocalCacheMode.CUSTOM
            ),
            role=iam_role,
        )

        cdk_crawler = codebuild.PipelineProject(
            self,
            config["appPrefix"] + "Crawler",
            build_spec=codebuild.BuildSpec.from_asset(
                "../01_crawler/buildspec.yml"
            ),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
            ),
            # we are switching to config file
            environment_variables={
                "S3_BUCKET": codebuild.BuildEnvironmentVariable(
                    value=f"s3://{bucket_name}"
                ),
                "APP_PREFIX": codebuild.BuildEnvironmentVariable(
                    value=config['appPrefix']
                )
            },
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.DOCKER_LAYER, codebuild.LocalCacheMode.CUSTOM
            ),
            role=iam_role,
            timeout=Duration.minutes(300),
        )

        ingestion_step_kwargs = {}

        if opensearch_domain_vpc:
            ingestion_sg = ec2.SecurityGroup(
                self,
                "OpenSearchIngestionPipelineSecurityGroup",
                vpc=opensearch_domain_vpc.vpc,
                description="Security group for ingestion step of the CodePipeline.",
                allow_all_outbound=True,
                disable_inline_rules=True,
            )

            opensearch_domain_sg = ec2.SecurityGroup.from_security_group_id(self, "OpenSearchIngestionDomainSGImport", opensearch_domain_vpc.security_group_id,
                mutable=True
            )


            opensearch_domain_sg.add_ingress_rule(ingestion_sg, ec2.Port.tcp(443), "Allow HTTPS access from ingestion pipeline.")

            ingestion_step_kwargs = {
                "vpc": opensearch_domain_vpc.vpc,
                "security_groups": [ingestion_sg],
            }


        cdk_ingest_admin_ch = codebuild.PipelineProject(
            self,
            config["appPrefix"] + "CodeBuildIngest" + "AdminCH",
            build_spec=codebuild.BuildSpec.from_asset(
                "../02_ingestion/buildspec_admin_ch.yml"
            ),
            environment=codebuild.BuildEnvironment(build_image=build_image),
            environment_variables={
                "S3_BUCKET": codebuild.BuildEnvironmentVariable(
                    value=f"s3://{bucket_name}"
                ),
                "OPENSEARCH_INDEX_NAME": codebuild.BuildEnvironmentVariable(
                    value=config["opensearch"]["index"]
                ),
                "OPENSEARCH_SECRET_NAME": codebuild.BuildEnvironmentVariable(
                    value=f"{config['appPrefix']}OpenSearchCredentials"
                ),
                "OPENSEARCH_DOMAIN_NAME": codebuild.BuildEnvironmentVariable(
                    value=f"{config['appPrefix']}{config['opensearch']['domain']}"
                ),
                "ENDPOINT_NAME": codebuild.BuildEnvironmentVariable(
                    value=config["appPrefix"] + config["sagemaker"]["embeddings_endpoint_name"]
                ),
                "APP_PREFIX": codebuild.BuildEnvironmentVariable(
                    value=config['appPrefix']
                ),
                "EMBEDDING_TYPE": codebuild.BuildEnvironmentVariable(
                    value=config["embedding"]["type"]),
                "BEDROCK_REGION": codebuild.BuildEnvironmentVariable(
                    value=config["bedrock_region"]),
                "BEDROCK_EMBEDDING_MODEL": codebuild.BuildEnvironmentVariable(
                    value=config["embedding"]["model"] if config["embedding"]["type"] == "Bedrock" else ""),
            },
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.DOCKER_LAYER, codebuild.LocalCacheMode.CUSTOM
            ),
            role=iam_role,
            timeout=Duration.minutes(300),
            **ingestion_step_kwargs,
        )
        cdk_ingest_fin_analyzer = codebuild.PipelineProject(
            self,
            config["appPrefix"] + "CodeBuildIngest" + "FinAnalyzer",
            build_spec=codebuild.BuildSpec.from_asset(
                "../02_ingestion/buildspec_fin_analyzer.yml"
            ),
            environment=codebuild.BuildEnvironment(build_image=build_image),
            environment_variables={
                "S3_BUCKET": codebuild.BuildEnvironmentVariable(
                    value=core.data_sources_bucket.bucket_name
                ),
                "S3_PREFIX": codebuild.BuildEnvironmentVariable(
                    value=config["fin_analyzer"]["s3"]["prefix"] if "fin_analyzer" in config and "s3" in config["fin_analyzer"] else ""
                ),
                "OPENSEARCH_INDEX_NAME": codebuild.BuildEnvironmentVariable(
                    value=config["fin_analyzer"]["index"] if "fin_analyzer" in config else ""
                ),
                "OPENSEARCH_SECRET_NAME": codebuild.BuildEnvironmentVariable(
                    value=f"{config['appPrefix']}OpenSearchCredentials"
                ),
                "OPENSEARCH_DOMAIN_NAME": codebuild.BuildEnvironmentVariable(
                    value=f"{config['appPrefix']}{config['opensearch']['domain']}"
                ),
                "ENDPOINT_NAME": codebuild.BuildEnvironmentVariable(
                    value=config["appPrefix"] + config["sagemaker"]["embeddings_endpoint_name"]
                ),
                "APP_PREFIX": codebuild.BuildEnvironmentVariable(
                    value=config['appPrefix']
                ),
                "EMBEDDING_TYPE": codebuild.BuildEnvironmentVariable(
                    value=config["embedding"]["type"]),
                "BEDROCK_REGION": codebuild.BuildEnvironmentVariable(
                    value=config["bedrock_region"]),
                "BEDROCK_EMBEDDING_MODEL": codebuild.BuildEnvironmentVariable(
                    value=config["embedding"]["model"] if config["embedding"]["type"] == "Bedrock" else ""),
                "APIS_SECRET": codebuild.BuildEnvironmentVariable(
                    value=fin_analyzer_apis.secret_name if "fin_analyzer" in config else "")
            },
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.DOCKER_LAYER, codebuild.LocalCacheMode.CUSTOM
            ),
            role=iam_role,
            timeout=Duration.minutes(300),
            **ingestion_step_kwargs,
        )

       
        source_embeddings_output = codepipeline.Artifact()
        source_crawler_output = codepipeline.Artifact()
        source_ingestion_output = codepipeline.Artifact()

        stages = [
            codepipeline.StageProps(
                stage_name="Source",
                actions=[
                    codepipeline_actions.CodeCommitSourceAction(
                        action_name="EmbeddingSource",
                        output=source_embeddings_output,
                        repository=repo_embeddings,
                        branch="main",
                        role=iam_role,
                    ),
                    codepipeline_actions.CodeCommitSourceAction(
                        action_name="CrawlerSource",
                        output=source_crawler_output,
                        repository=repo_crawler,
                        branch="main",
                        role=iam_role,
                    ),
                    codepipeline_actions.CodeCommitSourceAction(
                        action_name="IngestionSource",
                        output=source_ingestion_output,
                        repository=repo_ingestion,
                        branch="main",
                        role=iam_role,
                    ),
                ],
            ),
        ]

        if config["embedding"]["type"] == "Sagemaker":
            stages.append(
                codepipeline.StageProps(
                    stage_name="SageMakerEmbeddingsEndpoint",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="Embeddings",
                            project=cdk_deploy,
                            input=source_embeddings_output,
                            outputs=[codepipeline.Artifact("Build")],
                            role=iam_role,
                        )
                    ],
                )
            )
            stages.append(
                codepipeline.StageProps(
                    stage_name="DeployEmbeddingsSageMakerEndpoint",
                    actions=[
                        codepipeline_actions.CloudFormationCreateUpdateStackAction(
                            action_name="PrepareChanges",
                            stack_name=config["appPrefix"]
                            + "EmbeddingsSageMakerDeployment",
                            admin_permissions=True,
                            replace_on_failure=True,
                            template_path=codepipeline.Artifact("Build").at_path(
                                "exported-template.yml"
                            ),
                            template_configuration=codepipeline.Artifact(
                                "Build"
                            ).at_path("config.json"),
                            run_order=1,
                        ),
                    ],
                )
            )

        stages.append(
            codepipeline.StageProps(
                stage_name="Crawler",
                actions=[
                    codepipeline_actions.CodeBuildAction(
                        action_name="Crawl",
                        project=cdk_crawler,
                        input=source_crawler_output,
                        role=iam_role,
                    )
                ],
            ))

        stages.append(
            codepipeline.StageProps(
                stage_name="Ingestion",
                actions=[
                    codepipeline_actions.CodeBuildAction(
                        action_name="IngestAdminCH",
                        project=cdk_ingest_admin_ch,
                        input=source_ingestion_output,
                        role=iam_role,
                    ), 
                    codepipeline_actions.CodeBuildAction(
                        action_name="IngestFinAnalyzer",
                        project=cdk_ingest_fin_analyzer,
                        input=source_ingestion_output,
                        role=iam_role,
                    )
                ],
        ))

        codepipeline.Pipeline(
            self,
            "Pipeline",
            role=iam_role,
            artifact_bucket=s3_bucket,
            stages=stages,
        )
