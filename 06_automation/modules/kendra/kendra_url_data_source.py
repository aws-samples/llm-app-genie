# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin

from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kendra as kendra
from constructs import Construct


class KendraUrlDataSource(Construct):
    """
    Class that buils a construct that creates a kendra data source that uses urls.
    This is WEBCRAWLER v1 and will not be used.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        index_id: str,
        urls: str,
        crawler_depth: int,
        data_source_name: str = "WebDataSource",
    ) -> None:
        super().__init__(scope, id)

        index_arn = f"arn:aws:kendra:{Stack.of(self).region}:{Stack.of(self).account}:index/{index_id}"

        # Create an IAM role for the kendra data source
        kendra_data_source_role = iam.Role(
            self,
            "KendraDataSourceRole",
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

        # Create a data web-based Kendra data source
        kendra.CfnDataSource(
            self,
            "PublicWebSiteDataSource",
            index_id=index_id,
            name=data_source_name,
            type="WEBCRAWLER",
            role_arn=kendra_data_source_role.role_arn,
            data_source_configuration=kendra.CfnDataSource.DataSourceConfigurationProperty(
                web_crawler_configuration=kendra.CfnDataSource.WebCrawlerConfigurationProperty(
                    urls=kendra.CfnDataSource.WebCrawlerUrlsProperty(
                        seed_url_configuration=kendra.CfnDataSource.WebCrawlerSeedUrlConfigurationProperty(
                            seed_urls=urls, web_crawler_mode="SUBDOMAINS"
                        )
                    ),
                    crawl_depth=crawler_depth,
                )
            ),
        )
