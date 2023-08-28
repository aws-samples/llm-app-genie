"""
    CDK construct that creates a Kendra data source that uses site maps.
"""
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin


from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import custom_resources as cr
from aws_cdk.aws_iam import PolicyStatement
from constructs import Construct
from modules.config import config


class KendraDataSource(Construct):
    """
    Class that buils a construct that creates a kendra data source that uses site maps.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        index_id: str,
        data_source_name: str = "WebDataSource",
        config: dict = None,
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
        index_arn = f"arn:aws:kendra:{Stack.of(self).region}:{Stack.of(self).account}:index/{index_id}"

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

        cr_data_source = cr.AwsCustomResource(
            self,
            "KendraWebDataSource" + data_source_name,
            on_create=cr.AwsSdkCall(
                service="Kendra",
                action="createDataSource",
                parameters={
                    "IndexId": index_id,
                    "Name": data_source_name,
                    "Type": "TEMPLATE",
                    # "Configuration": self._get_default_config(),
                    "Configuration": self.config,
                    "RoleArn": data_source_role.role_arn,
                },
                physical_resource_id=cr.PhysicalResourceId.from_response("Id"),
            ),
            on_update=cr.AwsSdkCall(
                service="Kendra",
                action="updateDataSource",
                parameters={
                    # Get the data source ID from the experimental resource
                    "Id": cr.PhysicalResourceIdReference(),
                    "IndexId": index_id,
                    "Name": data_source_name,
                    "Type": "TEMPLATE",
                    # "Configuration": self._get_default_config(),
                    "Configuration": self.config,
                },
            ),
            on_delete=cr.AwsSdkCall(
                service="Kendra",
                action="deleteDataSource",
                parameters={
                    "Id": cr.PhysicalResourceIdReference(),
                    "IndexId": index_id,
                },
            ),
            # Policy that allows the experimental resource Lambda function to manage the Kendra data source
            # and pass the role to the data source
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    PolicyStatement(
                        actions=[
                            "kendra:CreateDataSource",
                            "kendra:DeleteDataSource",
                            "kendra:DescribeDataSource",
                            "kendra:UpdateDataSource",
                            "kendra:ListTagsForResource",
                        ],
                        resources=[
                            f"arn:aws:kendra:{Stack.of(self).region}:{Stack.of(self).account}:index/{index_id}",
                            f"arn:aws:kendra:{Stack.of(self).region}:{Stack.of(self).account}:index/{index_id}/data-source/*",
                        ],
                    ),
                    PolicyStatement(
                        actions=["iam:PassRole"], resources=[data_source_role.role_arn]
                    ),
                ]
            ),
        )

        cr.AwsCustomResource(
            self,
            "KendraDataSourceSyncJob" + data_source_name,
            on_create=cr.AwsSdkCall(
                service="Kendra",
                action="StartDataSourceSyncJob",
                parameters={
                    "Id": cr_data_source.get_response_field("Id"),
                    "IndexId": index_id,
                },
                physical_resource_id=cr.PhysicalResourceId.of("start-sync-job"),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    PolicyStatement(
                        actions=["kendra:StartDataSourceSyncJob"],
                        resources=[
                            f"arn:aws:kendra:{Stack.of(self).region}:{Stack.of(self).account}:index/{index_id}",
                            f"arn:aws:kendra:{Stack.of(self).region}:{Stack.of(self).account}:index/{index_id}/data-source/*",
                        ],
                    )
                ]
            ),
        )

    # def _get_default_config(self):
    #     # self.config = config["kendra"]["data_sources"]

    #     if self.urls is not None and len(self.urls) > 0:
    #         self.config["TemplateConfiguration"]["Template"]["connectionConfiguration"]["repositoryEndpointMetadata"]["seedUrlConnections"] = self.urls
    #         if ("siteMapUrls" in self.config["TemplateConfiguration"]["Template"]["connectionConfiguration"]["repositoryEndpointMetadata"]):
    #             del self.config["TemplateConfiguration"]["Template"]["connectionConfiguration"]["repositoryEndpointMetadata"]["siteMapUrls"]
    #         if ("s3SiteMapUrl" in self.config["TemplateConfiguration"]["Template"]["connectionConfiguration"]["repositoryEndpointMetadata"]):
    #             del self.config["TemplateConfiguration"]["Template"]["connectionConfiguration"]["repositoryEndpointMetadata"]["s3SiteMapUrl"]

    #     elif self.sitemap_urls is not None and len(self.sitemap_urls) > 0:
    #         self.config["TemplateConfiguration"]["Template"]["connectionConfiguration"]["repositoryEndpointMetadata"]["siteMapUrls"] = self.sitemap_urls

    #     return self.config
