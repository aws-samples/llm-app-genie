# 06 Automation

- We are using [trunk.io](https://docs.trunk.io/check) to check the code, to validate the code, run the below command

```bash
trunk check 06_automation/
```

- Check and update if required the environmnet parameters in _config/env_code.json_:

```python
{
  "globalTags": {
    "version": "1.2.0",
    "app": "demo",
    "owner": "gena-team",
    "deployment": "True"
  },
  "bedrock_region": "us-west-2",
  "customer": {
    "name": "SwissGov"
  },
  "opensearch": {
    "domain": "KB",
    "instance_type": "t3.medium.search",
    "index":"press-releases-en"
  },
  "sagemaker": {
    # Instance type for calculating the embeddings
    # If you use a different instance type without local storage volume you should add a KMS Key in th AWS::SageMaker::EndpointConfig in 00_llm_endpoint_setup/codebuild/embeddings/endpoint-config-template.yml. See also https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-endpointconfig.html#cfn-sagemaker-endpointconfig-kmskeyid
    "embeddings_instance_type": "ml.g4dn.xlarge",
    # Name of the endpoint to compute the endpoint
    "embeddings_endpoint_name": "EmbeddingsE5Large",
    # We recommend either a ml.g5.12xlarge or a ml.g5.48xlarge for the Falcon 40B instruct LLM
    # If you use a different instance type without local storage volume you should add a KMS Key in th AWS::SageMaker::EndpointConfig in 00_llm_endpoint_setup/codebuild/embeddings/endpoint-config-template.yml. See also https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-endpointconfig.html#cfn-sagemaker-endpointconfig-kmskeyid
    "llm_instance_type": "ml.g5.12xlarge",
    # Name of the endpoint that hosts the LLM
    "llm_endpoint_name": "Falcon40bInstruct12xlarge"
  },
  "kendra": {
    # Edition of the Kendra index (DEVELOPER_EDITION or ENTERPRISE EDITION)
    "kendra_edition": "DEVELOPER_EDITION",
    "index": "KnowledgeBase",
    # Kendra datasources JSON in the format documented:
    # https://docs.aws.amazon.com/kendra/latest/dg/ds-schemas.html#ds-schema-web-crawler
    # multiple datasource can be added to array
    "data_sources": [
      {
        "name": "press-releases-en",
        "TemplateConfiguration": {
          "Template": {
            "connectionConfiguration": {
              "repositoryEndpointMetadata": {
                "s3SeedUrl": null,
                # Website to be crawled: will be used to populate the Kendra Index
                # OpenSearch crawler has independent setup
                "seedUrlConnections": [
                  {
                    "seedUrl": "https://www.admin.ch/gov/en/start/documentation/media-releases.html?dyn_pageIndex=0"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/en/start/documentation/media-releases.html?dyn_pageIndex=1"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/en/start/documentation/media-releases.html?dyn_pageIndex=2"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/en/start/documentation/media-releases.html?dyn_pageIndex=3"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/en/start/documentation/media-releases.html?dyn_pageIndex=4"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/en/start/documentation/media-releases.html?dyn_pageIndex=5"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/en/start/documentation/media-releases.html?dyn_pageIndex=6"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/en/start/documentation/media-releases.html?dyn_pageIndex=7"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/en/start/documentation/media-releases.html?dyn_pageIndex=8"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/en/start/documentation/media-releases.html?dyn_pageIndex=9"
                  }
                ],
                # List of website sitemaps, working in Kendra only for the momment
                # Make sure to use either sitemaps or urls, Kendra doesn't support both for the same data source
                # Pay attation to format difference, below sitemaps are example only.
                "siteMapUrls": [
                    "https://www.admin.ch/gov/en/sitemap1.xml",
                    "https://www.admin.ch/gov/en/sitemap2.xml"
                ],
                "s3SiteMapUrl": null,
                "authentication": "NoAuthentication"
              }
            },
            "enableIdentityCrawler": false,
            "syncMode": "FULL_CRAWL",
            "additionalProperties": {
              "inclusionFileIndexPatterns": [],
              "rateLimit": "100",
              "maxFileSize": "50",
              "crawlDepth": "1",
              "crawlAllDomain": false,
              "crawlSubDomain": true,
              "inclusionURLIndexPatterns": [],
              "exclusionFileIndexPatterns": [],
              "proxy": {},
              "exclusionURLCrawlPatterns": [],
              "exclusionURLIndexPatterns": [],
              "crawlAttachments": true,
              "honorRobots": true,
              "inclusionURLCrawlPatterns": [],
              "maxLinksPerUrl": "150"
            },
            "type": "WEBCRAWLERV2",
            "version": "1.0.0",
            "repositoryConfigurations": {
              "attachment": {
                "fieldMappings": [
                  {
                    "dataSourceFieldName": "category",
                    "indexFieldName": "_category",
                    "indexFieldType": "STRING"
                  },
                  {
                    "dataSourceFieldName": "sourceUrl",
                    "indexFieldName": "_source_uri",
                    "indexFieldType": "STRING"
                  }
                ]
              },
              "webPage": {
                "fieldMappings": [
                  {
                    "dataSourceFieldName": "category",
                    "indexFieldName": "_category",
                    "indexFieldType": "STRING"
                  },
                  {
                    "dataSourceFieldName": "sourceUrl",
                    "indexFieldName": "_source_uri",
                    "indexFieldType": "STRING"
                  }
                ]
              }
            }
          }
        }
      },
      {
        "name": "press-releases-de",
        "TemplateConfiguration": {
          "Template": {
            "connectionConfiguration": {
              "repositoryEndpointMetadata": {
                "s3SeedUrl": null,
                "seedUrlConnections": [
                  {
                    "seedUrl": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.html?dyn_pageIndex=0"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.html?dyn_pageIndex=1"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.html?dyn_pageIndex=2"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.html?dyn_pageIndex=3"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.html?dyn_pageIndex=4"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.html?dyn_pageIndex=5"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.html?dyn_pageIndex=6"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.html?dyn_pageIndex=7"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.html?dyn_pageIndex=8"
                  },
                  {
                    "seedUrl": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.html?dyn_pageIndex=9"
                  }
                ],
                "siteMapUrls": [],
                "s3SiteMapUrl": null,
                "authentication": "NoAuthentication"
              }
            },
            "enableIdentityCrawler": false,
            "syncMode": "FULL_CRAWL",
            "additionalProperties": {
              "inclusionFileIndexPatterns": [],
              "rateLimit": "100",
              "maxFileSize": "50",
              "crawlDepth": "1",
              "crawlAllDomain": false,
              "crawlSubDomain": true,
              "inclusionURLIndexPatterns": [],
              "exclusionFileIndexPatterns": [],
              "proxy": {},
              "exclusionURLCrawlPatterns": [],
              "exclusionURLIndexPatterns": [],
              "crawlAttachments": true,
              "honorRobots": true,
              "inclusionURLCrawlPatterns": [],
              "maxLinksPerUrl": "150"
            },
            "type": "WEBCRAWLERV2",
            "version": "1.0.0",
            "repositoryConfigurations": {
              "attachment": {
                "fieldMappings": [
                  {
                    "dataSourceFieldName": "category",
                    "indexFieldName": "_category",
                    "indexFieldType": "STRING"
                  },
                  {
                    "dataSourceFieldName": "sourceUrl",
                    "indexFieldName": "_source_uri",
                    "indexFieldType": "STRING"
                  }
                ]
              },
              "webPage": {
                "fieldMappings": [
                  {
                    "dataSourceFieldName": "category",
                    "indexFieldName": "_category",
                    "indexFieldType": "STRING"
                  },
                  {
                    "dataSourceFieldName": "sourceUrl",
                    "indexFieldName": "_source_uri",
                    "indexFieldType": "STRING"
                  }
                ]
              }
            }
          }
        }
      }
    ]
  }
}
```

- Setup the required configuration, the default configuration is **dev**, you can have many configuration files and use the `STAGE` environment variable to specify which configuration file to use, **dev** is default value::

```bash
export STAGE=env_code
```

- CDK is using the default AWS_REGION and AWS_ACCOUNT for deployment, to deploy into another account update the defaul account

```bash
aws configure get region
aws sts get-caller-identity --query Account --output text
# or
cat ~/.aws/config
```

-- There are 2 additional parameters to control the naming of the stacks, the final name will be: **CDK_APP_PREFIX + StackId**

```bash
export CDK_APP_PREFIX=Gena # Application code will be added to stack names
```

- To deploy chatbot into an existing VPC set `"existing_vpc_id"` property in the config json file.

```json
{
  // ... other config
  "existing_vpc_id": "vpc-1234567890abcdefg"
}
```
