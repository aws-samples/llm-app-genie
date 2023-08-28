# Automated deployment of the knowledge base

There are two types of knowledge bases in this solution based on two AWS services: Amazon Kendra and Amazon OpenSearch Service

## Deploying Amazon Kendra

The knowledge base is based on two CDK stacks, one for an [Amazon Kendra](https://docs.aws.amazon.com/kendra/latest/dg/what-is-kendra.html) index and another for its data sources.

The CDK stack in `kendra_index_stack.py` deploys an Amazon Kendra index and names it after a the customer name, which you can input as a stack parameter.
By default, this Kendra index uses the Developer **Edition version**. This version can index up to **10,000 documents** and run a maximum of **4,000 queries per day**. It costs **$810 per month**.

The CDK stack in `kendra_data_sources_stack.py` takes an Amazon Kendra index ID as a parameter and adds data sources to it. At the moment, it adds one data source based on the WEBCRAWLERV2 data source type. This type of data source allows advanced configurations such as using authentication. However, it is not supported in AWS CloudFormation, so this stack uses a CDK custom resource which is defined in a CDK construct in `kendra_sitemap_data_source.py`.

### KendraSitemapDataSource

This CDK Construct builds an Amazon Kendra data source that takes a list of site map URLs. These URLs should point to an XML file that map the content of the website.

For code clarity, the settings of the data source are in the `template_configuration.json` file. You can modify settings there and redeploy the stack for updating your data source. The schema of such settings is available in the [Amazon Kendra Web Crawler template schema documentation](https://docs.aws.amazon.com/kendra/latest/dg/ds-schemas.html#ds-schema-web-crawler)

### Deployment instructions

Run the following command in a shell with the [AWS CDK Toolkit](https://docs.aws.amazon.com/cdk/v2/guide/cli.html) installed:

```shell
cdk deploy KendraIndexStack KendraDataSourcesStack --parameters KendraIndexStack:CustomerName=<CustomerName> --parameters KendraDataSourcesStack:SitemapUrls=https://example1.com/sitemap.xml,https://example2.com/sitemap.xml
```

## Deploying Amazon OpenSearch Service

**To deploy the OpenSearch index, follow the instructions in [Deploy the knowledge base](../../README.md#deploy-the-knowledge-base).**
