from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct
from modules.config import config, quotas, quotas_client
from modules.stack import GenAiStack
import logging

stack = {
    "description": "MLOps Pipeline to deploy LLM to SageMaker inference endpoint",
    "tags": {},
}



class LLMSageMakerStack(GenAiStack):
    """A root construct which represents a codepipeline CloudFormation stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        # check for required instance quate in account
        response = quotas_client.get_service_quota(
            ServiceCode="sagemaker",
            QuotaCode=quotas[config["sagemaker"]["llm_instance_type"]],
        )
        if response["Quota"]["Value"] == 0.0:
            logging.fatal(f"Please adjust your quota for the LLM Endpoint for type {config['sagemaker']['llm_instance_type']}")
            return
        else:
            print(
                f"You have enough instances quotas for the LLM Endpoint of type {config['sagemaker']['llm_instance_type']}"
            )

        repo = codecommit.Repository(
            self,
            "Repository",
            repository_name=config["appPrefix"]+"LlmSagemaker",
            code=codecommit.Code.from_directory(
                "../00_llm_endpoint_setup/codebuild/llm", branch="main"
            ),
        )

        # should we name the S3 bucket?
        s3_bucket = s3.Bucket(
            self,
            "Bucket",
            versioned=False,
            bucket_name=f"{config['appPrefixLowerCase']}-sagemaker-llm-falcon-artifact-{self.region}-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        build_image = codebuild.LinuxBuildImage.STANDARD_7_0

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
            ],
        )

        cdk_deploy = codebuild.PipelineProject(
            self,
            config["appPrefix"] + "SageMakerLLMEndpoint",
            build_spec=codebuild.BuildSpec.from_asset(
                "../00_llm_endpoint_setup/codebuild/llm/buildspec.yml"
            ),
            environment=codebuild.BuildEnvironment(build_image=build_image),
            environment_variables=(
                {
                    "S3_BUCKET": codebuild.BuildEnvironmentVariable(
                        value=f"s3://{s3_bucket.bucket_name}"
                    ),
                    "MODEL_EXECUTION_ROLE_ARN": codebuild.BuildEnvironmentVariable(
                        value=iam_role.role_arn
                    ),
                    "INSTANCE_TYPE": codebuild.BuildEnvironmentVariable(
                        value=config["sagemaker"]["llm_instance_type"]
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
                        value=config["appPrefix"] + config["sagemaker"]["llm_endpoint_name"]
                    ),
                }
            ),
            description="Deploy SageMaker Falcon 40B endpoint",
            timeout=Duration.minutes(120),
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.DOCKER_LAYER, codebuild.LocalCacheMode.CUSTOM
            ),
            role=iam_role,
        )

        source_output = codepipeline.Artifact()

        codepipeline.Pipeline(
            self,
            "Pipeline",
            role=iam_role,
            artifact_bucket=s3_bucket,
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        codepipeline_actions.CodeCommitSourceAction(
                            action_name="Source",
                            output=source_output,
                            repository=repo,
                            branch="main",
                            role=iam_role,
                        )
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="SageMakerLLMEndpointSetup",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="LLM",
                            project=cdk_deploy,
                            input=source_output,
                            outputs=[codepipeline.Artifact("Build")],
                            role=iam_role,
                        )
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="DeployLLMSageMakerEndpoint",
                    actions=[
                        codepipeline_actions.CloudFormationCreateUpdateStackAction(
                            action_name="PrepareChanges",
                            stack_name=config["appPrefix"] + "LLMSageMakerDeployment",
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
                ),
            ],
        )
