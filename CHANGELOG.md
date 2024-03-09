# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- N/A
- 

## [1.2.1] - 2024-03-09

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
