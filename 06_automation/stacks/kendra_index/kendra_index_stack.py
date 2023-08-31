import aws_cdk.aws_iam as iam
import aws_cdk.aws_kendra as kendra

# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin
from aws_cdk import CfnTag, RemovalPolicy
from constructs import Construct
from modules.config import config
from modules.stack import GenAiStack

stack = {"description": f"Kendra Index for {config['appPrefix']}:", "tags": {}}


class KendraIndexStack(GenAiStack):
    """
    Class that creates a Kendra index.
    """

    # Class attribute to keep the index construct
    index: kendra.CfnIndex = None

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        # Create an IAM role for a Kendra index in CDK
        # with required permissions to write CloudWatch logs and metrics
        kendra_role = iam.Role(
            self,
            config["appPrefix"] + "KendraRole",
            assumed_by=iam.ServicePrincipal("kendra.amazonaws.com"),
            inline_policies={
                config["appPrefix"]
                + "KendraCloudWatchPolicy": iam.PolicyDocument(
                    statements=[
                        # IAM policy to allow creating log groups
                        iam.PolicyStatement(
                            actions=["logs:CreateLogGroup"],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/kendra/*"
                            ],
                        ),
                        # IAM policy to allow describing log groups
                        iam.PolicyStatement(
                            actions=["logs:DescribeLogGroups"], resources=["*"]
                        ),
                        # IAM policy to allow writing to CloudWatch metrics
                        iam.PolicyStatement(
                            actions=["cloudwatch:PutMetricData"],
                            resources=["*"],
                            conditions={
                                "StringEquals": {"cloudwatch:namespace": "AWS/Kendra"}
                            },
                        ),
                        # IAM policy to allow writing to CloudWatch log streams
                        iam.PolicyStatement(
                            actions=[
                                "logs:CreateLogStream",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "logs:DescribeLogStreams",
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/kendra/*:log-stream:*"
                            ],
                        ),
                    ]
                ),
            },
        )

        # Create a Kendra index
        customer_name = config["customer"]["name"]
        edition = config["kendra"]["kendra_edition"]
        self.index = kendra.CfnIndex(
            self,
            config["appPrefix"] + "KnowledgeBaseKendra",
            name=f"kendra-knowledge-base-{customer_name}",
            role_arn=kendra_role.role_arn,
            edition=edition,
            description=f"Knowledge base for {customer_name}",
            tags=[
                CfnTag(
                    key=f"{config['appPrefixLC']}:friendly-name",
                    value=f"Amazon Kendra index - {customer_name}",
                )
            ],
        )

        # Set removal policy to retain on delete
        self.index.apply_removal_policy(RemovalPolicy.DESTROY)