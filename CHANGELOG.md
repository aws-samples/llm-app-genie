# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- N/A
- 

## [1.3.6] - 2024-07-15



### Added

- feat(Fin Analyzer): update documentation
- feat(Fin Analyzer): update ingestion pipeline
- feat(Fin Analyzer): automate data download logic
- feat(Fin Analyzer): move configuration to dev.json
- feat(Fin Analyzer): update crawler to include UBS, remove NFLX and TSLA
- feat: add CDK Core stack to manage common elements
- feat: filter models to only those with available setup
- feat: redesign OpenSearch retriever
- feat: add Flow control config
- perf: add chunking to embedding to double performance
- feat: add option to hide models (claude-3-opus) to avoid errors
- feat: add chatbot_name and logo customizations
- feat: add bedrock configuration for ingestion pipeline


### Fixed

- bug: fix embedding module import
- bug: fix Docker legacy warning
- bug: fix custom prompts and hints
- bug: fix query string filtering
- bug: add error handling for missing financial analyzer access in app.config
- bug: fix Kendra data source deployment

### Changed

- The release switches from a multi VPC deployment to a single VPC deployment. You will need to keep the existing OpenSearch domain in the OpenSearch VPC or migrate the OpenSearch domain to the chatbot VPC.
- refactor: rename admin.ch embedding files for clarity
- refactor: switch to one VPC
- refactor: move role policies to corresponding stacks
- refactor: move VPC to core stack
- refactor: remove unused Kendra URL data source
- refactor: move setup to appconfig.json, delete old hints.yaml
- refactor: move hardcoded RAG slider parameters to appconfig.json
- refactor: update Streamlit modules
- refactor: remove outdated Streamlit configurations
- refactor: update and refactor ingest.py for OpenSearch serverless and bedrock






## [1.2.1] - 2024-03-09

### Added

- Anthropic Claude 3

### Security

- Update dependencies to their latest versions

## [1.2.0] - 2024-03-08

### Added

- CDK stack to deploy OpenSearch domain into a VPC without internet connectivity. Chatbot connects to OpenSearch domain with a VPC endpoint.
- Adds cdk retetion policies to keep resources that store data (i.e. OpenSearch, S3 buckets) when cdk stacks get deleted
- Adds VPC flow logs
- CDK adds lifecycle rules and versioning to S3 bucket to follow best practices


### Fixed

- adapt Streamlit changes to query parameter API
- Streamlit breaking configuration parameters
- 02_ingestion ingest.py script 


### Changed

- Reduce IAM permissions of some IAM roles
- Improve duckduckgo agent
- Documentation about local deployment now uses a port that is less likely in use


### Deprecated

- CDK stack to deploy OpenSearch index with an internet facing endpoint may be removed in a future release.

## [1.1.1] - 2023-11-18

### Added

- Enable streaming responses with toggle
- Enable X-ray for agents
- update README to document fast and minimal deployment
- Support Llama 2 model in Amazon Bedrock

## [1.1.0] - 2023-11-10

### Added

- Additional libraries
- Support for PDF parsing through Amazon Textract langchain integration with markdown output formatting in upload document mode
- Creation of new "Flow" to support Langchain Agents
    - First implementation of Financial Analysis and SQL query generator agents
- Expose to the UI the number of documents to be retrieved in RAG mode
- 


### Fixed

- Improved documentation
- Increase version of libraries

### Changed

- Renamed to "LLM APP Genie"
- Use public Amazon Bedrock SDK

### Removed

- N/A

## [1.0.4] - 2023-10-12

### Added

- LLMConfig, LLMConfigParameters, LLMConfigMap classes to handle configurations

### Fixed

- Improved documentation
- Increase version of libraries

### Changed

- Renamed to "LLM APP Genie"
- Use public Amazon Bedrock SDK

### Removed

- N/A

## [1.0.3] - 2023-09-29

Initial release
