from aws_cdk import App, Environment, Stack, SecretValue, RemovalPolicy, Duration
import aws_cdk.aws_iam as iam
import aws_cdk.aws_secretsmanager as sm
import aws_cdk.aws_s3 as s3
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from constructs import Construct
from modules.config import config
from modules.stack import GenAiStack

stack = {
    "description": "Deploy Pipeline to deploy Genie full infrastructure",
    "tags": {},
}


class DeploymentPipelineStack(GenAiStack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        repo = codecommit.Repository(
            self,
            config["appPrefix"] + "Repo",
            repository_name=config["appPrefix"] + "-repo"
        )

        user = iam.User(self, 'mirror-user')

        user.attach_inline_policy(
            iam.Policy(
                self,
                config["appPrefix"] + "PolicyForMirrorRepo",
                statements=[iam.PolicyStatement(
                    actions=["codecommit:GitPull", "codecommit:GitPush"],
                    resources=[repo.repository_arn]
                )]
            )
        )

        access_key = iam.AccessKey(self, 'genie-mirror-user-access-key', user=user)

        sm.Secret(
            self,
            config["appPrefix"] + "MirrorUserCredentials",
            secret_object_value={
                "access_key": SecretValue.unsafe_plain_text(access_key.access_key_id),
                "secret_key": access_key.secret_access_key
            }
        )

        s3_bucket = s3.Bucket(
            self,
            "ArtifactBucket",
            versioned=False,
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
                iam.ServicePrincipal("cloudformation.amazonaws.com"),
                iam.ServicePrincipal("codebuild.amazonaws.com"),
                iam.ServicePrincipal("codepipeline.amazonaws.com"),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
            ]
        )

        cdk_deploy = codebuild.PipelineProject(
            self,
            config["appPrefix"] + "DeployInfrastructure",
            build_spec=codebuild.BuildSpec.from_asset(
                "stacks/deployment_pipeline/buildspec-develop.yml"
            ),
            environment=codebuild.BuildEnvironment(build_image=build_image, privileged=True),
            environment_variables=(
                {
                    "LLM_STACK_NAME": codebuild.BuildEnvironmentVariable(
                        value=f"{config['appPrefix']}LlmPipelineStack",
                    ),
                    "INGESTION_STACK_NAME": codebuild.BuildEnvironmentVariable(
                        value=f"{config['appPrefix']}OpenSearchIngestionPipelineStack"
                    )
                }
            ),
            description="Deploy Genie Infrastructure",
            timeout=Duration.minutes(180), # 3h time limit
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.DOCKER_LAYER, codebuild.LocalCacheMode.CUSTOM
            ),
            role=iam_role,
        )

        source_output = codepipeline.Artifact()

        pipeline_name = config["appPrefix"]+"DeploymentPipeline"
        codepipeline.Pipeline(
            self,
            pipeline_name,
            pipeline_name=pipeline_name,
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
                            branch="develop",
                            role=iam_role,
                        )
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="DeployGenieFullInfrastructure",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="DeployInfrastructure",
                            project=cdk_deploy,
                            input=source_output,
                            outputs=[codepipeline.Artifact("Build")],
                            role=iam_role,
                        )
                    ],
                ),
            ],
        )

        prod_source_output = codepipeline.Artifact()
        cdk_prod_chatbot = codebuild.PipelineProject(
            self,
            "Prod"+config["appPrefix"]+"ChatbotCodebuild",
            build_spec=codebuild.BuildSpec.from_asset(
                "stacks/deployment_pipeline/buildspec-main.yml"
            ),
            environment=codebuild.BuildEnvironment(build_image=build_image, privileged=True),
            description="Deploy Genie Chatbot Prod",
            timeout=Duration.minutes(180),  # 3h time limit
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.DOCKER_LAYER, codebuild.LocalCacheMode.CUSTOM
            ),
            role=iam_role,
        )
        pipeline_name = "Prod"+config["appPrefix"]+"ChatbotPipeline"
        codepipeline.Pipeline(
            self,
            pipeline_name,
            pipeline_name=pipeline_name,
            role=iam_role,
            artifact_bucket=s3_bucket,
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        codepipeline_actions.CodeCommitSourceAction(
                            action_name="Source",
                            output=prod_source_output,
                            repository=repo,
                            branch="main",
                            role=iam_role,
                        )
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="DeployGenieProdChatbot",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="DeployProdChatbot",
                            project=cdk_prod_chatbot,
                            input=prod_source_output,
                            outputs=[codepipeline.Artifact("Build")],
                            role=iam_role,
                        )
                    ],
                ),
            ],
        )
