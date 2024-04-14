"""
    CDK construct that creates a Kendra data source that uses site maps.
"""

# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin


from aws_cdk import Stack, Duration, CustomResource
from aws_cdk import aws_iam as iam
from aws_cdk import custom_resources as cr
from aws_cdk.aws_iam import PolicyStatement
from constructs import Construct
from aws_cdk import aws_lambda_python_alpha as lambda_python
from aws_cdk import aws_lambda as lambda_
import json

class KendraDataSource(Construct):
    """
    Class that buils a construct that creates a kendra data source that uses site maps.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        index_id: str,
        index_arn: str,
        data_source_name: str = "WebDataSource",
        config: dict = None,
        tags: dict[str, str] = {},
        # urls: list[str] = None,
        # sitemap_urls: list[str] = None,
        # crawler_depth: str = "3",
    ) -> None:
        super().__init__(scope, id)

        self.index_id = index_id
        self.data_source_name = data_source_name
        self.config = config
        # self.sitemap_urls = sitemap_urls
        # self.urls = urls
        # self.crawler_depth = crawler_depth

        stack = Stack.of(self)
        region = stack.region
        account = stack.account

        # Create an IAM role for the kendra data source
        data_source_role = iam.Role(
            self,
            "KendraDataSourceRole" + data_source_name,
            assumed_by=iam.ServicePrincipal("kendra.amazonaws.com"),
            inline_policies={
                "KendraKnowledgeBaseDataSource": iam.PolicyDocument(
                    statements=[
                        # IAM policy to allow writing in the Kendra index
                        iam.PolicyStatement(
                            actions=[
                                "kendra:BatchPutDocument",
                                "kendra:BatchDeleteDocument",
                            ],
                            resources=[index_arn],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "kendra:PutPrincipalMapping",
                                "kendra:DeletePrincipalMapping",
                                "kendra:ListGroupsOlderThanOrderingId",
                                "kendra:DescribePrincipalMapping",
                            ],
                            resources=[index_arn, f"{index_arn}/data-source/*"],
                        ),
                    ]
                )
            },
        )

        data_source_function = lambda_python.PythonFunction(
            self,
            "CreateKendraDataSource",
            entry="./modules/kendra/data_source_lambda",
            index="function.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(amount=120),
        )

        is_complete_handler = lambda_python.PythonFunction(
            self,
            id=f"CreateKendraDataSourceIsComplete",
            runtime=lambda_.Runtime.PYTHON_3_12,
            entry="./modules/kendra/data_source_is_complete_lambda",
            index="function.py",
            handler="lambda_handler",
            timeout=Duration.seconds(amount=120),
        )

        provider = cr.Provider(
            self,
            "KendraDataSourceCustomResourceProvider",
            on_event_handler=data_source_function,
            is_complete_handler=is_complete_handler,
            query_interval=Duration.minutes(2),
        )


        data_source_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["kendra:CreateDataSource"],
                resources=[
                    index_arn,
                    f"{index_arn}/data-source/*"
                ]
            )
        )

        data_source_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=[
                    "kendra:UpdateDataSource",
                    "kendra:DeleteDataSource",
                    "kendra:TagResource",
				    "kendra:UntagResource",
				    "kendra:ListTagsForResource"
                ],
                resources=[
                    index_arn, 
                    f"{index_arn}/data-source/*"
                ],
            )
        )

        data_source_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["iam:PassRole"], resources=[data_source_role.role_arn]
            )
        )

        is_complete_handler.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["kendra:DescribeDataSource"],
                resources=[index_arn, f"{index_arn}/data-source/*"],
            )
        )

        custom_resource_tags = [{'Key': k, 'Value': v} for k, v in tags.items()]

        cr_data_source = CustomResource(
            self,
            "KendraDataSourceCustomResource",
            service_token=provider.service_token,
            properties={
                "name": data_source_name,
                "index_id": index_id,
                "config": json.dumps(self.config),
                "role_arn": data_source_role.role_arn,
                "tags": custom_resource_tags,
                "region": region,
                "account_id": account
            },
        )

       

        data_sync = cr.AwsCustomResource(
            self,
            "KendraDataSourceSyncJob" + data_source_name,
            on_create=cr.AwsSdkCall(
                service="Kendra",
                action="StartDataSourceSyncJob",
                parameters={
                    "Id": cr_data_source.ref,
                    "IndexId": index_id,
                },
                physical_resource_id=cr.PhysicalResourceId.of("start-sync-job"),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    PolicyStatement(
                        actions=["kendra:StartDataSourceSyncJob"],
                        resources=[
                            index_arn,
                            f"{index_arn}/data-source/*",
                        ],
                    )
                ]
            ),
        )

        data_sync.node.add_dependency(cr_data_source)


