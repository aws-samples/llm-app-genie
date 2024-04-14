# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin
# from aws_cdk import (
#     CfnParameter,
#     Tags
# )

import aws_cdk.aws_kendra as kendra
from constructs import Construct
from modules.config import config
from modules.kendra import KendraDataSource
from modules.stack import GenAiStack

stack = {
    "description": f"Kendra Data Source for {config['customer']['name']} website",
    "tags": {},
}


class KendraDataSourcesStack(GenAiStack):
    """Class that creates a Kendra index with a data source that uses site maps."""

    def __init__(
        self, scope: Construct, construct_id: str, index: kendra.CfnIndex, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, stack, **kwargs)
        index_id = index.ref
        index_arn = index.attr_arn

        all_tags = config["globalTags"] | stack["tags"]

        for ds in config["kendra"]["data_sources"]:
            urls = ds["TemplateConfiguration"]["Template"]["connectionConfiguration"][
                "repositoryEndpointMetadata"
            ]["seedUrlConnections"]
            sitemaps = ds["TemplateConfiguration"]["Template"][
                "connectionConfiguration"
            ]["repositoryEndpointMetadata"]["siteMapUrls"]

            name = ds["name"]
            del ds["name"]


            if urls is not None and len(urls) > 0:
                # transformed_list = [{"seedUrl": url} for url in urls]
                del ds["TemplateConfiguration"]["Template"]["connectionConfiguration"][
                    "repositoryEndpointMetadata"
                ]["siteMapUrls"]
                del ds["TemplateConfiguration"]["Template"]["connectionConfiguration"][
                    "repositoryEndpointMetadata"
                ]["s3SiteMapUrl"]

                KendraDataSource(
                    self,
                    name,
                    index_id=index_id,
                    index_arn=index_arn,
                    data_source_name=name,
                    config=ds,
                    tags=all_tags
                )

            # crawler accepts either urls or site maps
            elif sitemaps is not None and len(sitemaps) > 0:
                KendraDataSource(
                    self,
                    name,
                    index_id=index_id,
                    index_arn=index_arn,
                    data_source_name=name,
                    config=ds,
                    tags=all_tags
                )