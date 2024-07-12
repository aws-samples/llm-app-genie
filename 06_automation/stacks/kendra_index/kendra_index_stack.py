import aws_cdk.aws_iam as iam
import aws_cdk.aws_kendra as kendra

# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin
from aws_cdk import CfnTag, RemovalPolicy
from constructs import Construct
from modules.config import config
from modules.stack import GenAiStack
from stacks.core.core_stack import CoreStack

stack = {"description": f"Kendra Index for {config['appPrefix']}:", "tags": {}}


class KendraIndexStack(GenAiStack):
    """
    Class that creates a Kendra index.
    """

    # Class attribute to keep the index construct
    index: kendra.CfnIndex = None

    def __init__(self, scope: Construct, construct_id: str, core: CoreStack, **kwargs) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)

        # Update Application role to access Kendra
        core.role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kendra:Query", "kendra:ListTagsForResource"],
                resources=[f"arn:aws:kendra:{self.region}:{self.account}:index/*"],
            )
        )
        
        # # MM:: move to Kendra Stack
        # # Policy to allow listing Kendra indices
        core.role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kendra:ListIndices", "kendra:ListDataSources"],
                resources=["*"],
            )
        )
        # Policy statement to allow querying the Kendra indices that have the genie:deployment tag
        core.role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kendra:Query", "kendra:Retrieve"],
                resources=[f"arn:aws:kendra:{self.region}:{self.account}:index/*"],
                conditions={
                      "StringEquals": {f"aws:ResourceTag/genie:deployment": "True"}
                },
            )
        )



        # Create an IAM role for a Kendra index in CDK
        # with required permissions to write CloudWatch logs and metrics
        kendra_role = iam.Role(
            self,
            "KendraRole",
            assumed_by=iam.ServicePrincipal("kendra.amazonaws.com"),
            inline_policies={
                "KendraCloudWatchPolicy": iam.PolicyDocument(
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

        self.index = kendra.CfnIndex(
            self,
            id = f"{config['appPrefix']}{config['kendra']['index']}{customer_name}",
            name=f"{config['appPrefix']}{config['kendra']['index']}{customer_name}",
            role_arn=kendra_role.role_arn,
            edition=config["kendra"]["edition"],
            description=f"Knowledge base for {customer_name}",
            tags=[
                CfnTag(
                    key="genie:friendly-name",
                    value=f"Amazon Kendra index - {customer_name}",
                )
            ],
        )

        # Set removal policy to retain on delete
        self.index.apply_removal_policy(RemovalPolicy.DESTROY)