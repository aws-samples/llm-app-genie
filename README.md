# LLM App Genie - Get started building generative AI into your apps <a name="genie---generative-enterprise-assistant"></a>

## Table of contents <a name="table-of-contents"></a>

- [LLM App Genie - Get started building generative AI into your apps](#genie---generative-enterprise-assistant)
  - [Table of contents](#table-of-contents)
  - [Intro and Architecture](#introduction)
    - [Architecture Overview](#architecture-overview)
  - [Getting started](#getting-started)
    - [Fast, minimal, fully managed deployment](#minimal-deployment)
    - [Modular Deployment: Deploying individual components](#modular-deployment)
    - [Full deployment](#full-deployment)
    - [Common Deployment Scenarios](#common-deployment-scenarios)
  - [I need help](#i-need-help)
  - [Usage Scenarios](#usage-scenarios)
    - [How to populate knowledge bases?](#populate-knowledgebase)
    - [How to fine-tune a LLM?](#finetune)
    - [How to customize the chatbot?](#customize-chatbot)
  - [Costs and Clean up ](#costs-and-clean-up)
    - [Costs](#costs)
    - [Clean up](#clean-up)
  - [Setup development environment](#setup-development-environment)
    - [Pull Requests](#pull-requests)
    - [Repository structure](#repo_structure)
    - [Local Development Guide](#local-development-guide)
    - [Pre-requisites for Development](#pre-requisites-for-development)
  - [Troubleshooting/FAQ](#troubleshootingfaq)
  - [Copyright information](#copyright)

## Intro and Architecture <a name="introduction"></a>

LLM App Genie is a fully private chat companion which provides several functionalities, each of them providing a reference implementation of a dialog-based search bot using interchangeable large language models (LLMs).

It combines intelligent search with generative AI to give factual answers based on the private knowledge bases, APIs and SQL databases. 
The RAG search is based on [Amazon OpenSearch Service](https://aws.amazon.com/opensearch-service/) and [Amazon Kendra](https://aws.amazon.com/kendra/) services. 
The Agents implementation covers various open source APIs and an SQL query generator.
The solution also leverages [Streamlit](https://streamlit.io/) for the frontend and [Langchain](https://github.com/hwchase17/langchain) for the conversation flow to implement an interactive chat application.

The core features of this implementation are:

- Fully private Chatbot with generative AI capabilities on private data
- Flexible browser based webcrawler using scrapy and Playwright to download and ingest webpages from public and private sources into the knowledge base, see [full webcrawler feature list](./01_crawler/README.md#crawler)
- Support for different knowledge bases ([OpenSearch](https://aws.amazon.com/opensearch-service/) or [Amazon Kendra](https://aws.amazon.com/kendra/))
- Semantic Search with Amazon Kendra or custom vector embeddings with OpenSearch
- Support for Financial Analysis and SQL database query generator thgough Agents
- Fine-tuning of LLMs to increase model relevance and quality of answers
- Free choice of different LLMs and search engines
- End-to-end automated deployment using AWS CDK

The following screenshot shows the application user interface in RAG mode:
![Genie application user interface](05_doc/app-screenshot.png)

<div class=“alert alert-info”> 💡 Note: this solution will incur AWS costs. You can find more information about these costs in the Costs section.
</div>

### Architecture Overview <a name="architecture-overview"></a>

![](05_doc/companion_architecture_simple.drawio.png)

## Getting started <a name="getting-started"></a>

We provide infrastructure as code for the solution in [AWS CDK](https://aws.amazon.com/cdk/).

There are three main deployment types:

- [Fast, minimal, fully managed deployment](#minimal-deployment): Deploy and use AWS Managed services: use Amazon Kendra and Amazon Bedrock.
- [Modular deployment](#modular-deployment): Deploy each component (stack) individually.
- [Full deployment](#full-deployment): Deploy all components (stacks) of the solution.

**Step 0**: Pre-requisites <a name="pre_requisites"></a>

You need the following frameworks on your local computer. You can also use the [AWS Cloud9](https://aws.amazon.com/cloud9/) IDE for deployment and testing (choose the Ubuntu OS to have more dependencies already installed).

- Node version 18 or higher
- [AWS CDK](https://aws.amazon.com/cdk/) version `2.91.0` or higher (latest tested CDK version is `2.91.0`)
- Python 3.10
- [Python Poetry](https://python-poetry.org/)
- [Docker](https://www.docker.com/)

If using Cloud9, first increase the disk space to allow CDK to use `docker` and pull images without problems:
```
curl -o resize.sh https://raw.githubusercontent.com/aws-samples/semantic-search-aws-docs/main/cloud9/resize.sh
chmod +x ./resize.sh
./resize.sh 50

```

To install Node 18 or higher:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
nvm install 18.18.1
```

To install the latest AWS CDK version:

```bash
npm install -g aws-cdk
```

To install `Python Poetry`, or see [poetry installation details](https://python-poetry.org/docs/):

- Linux, macOS, Windows (WSL):
  ```bash
  curl -sSL https://install.python-poetry.org | python3.10 -
  ```
- Windows (Powershell)
  ```sh
  (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
  ```

To clone the GitHub repository:

```sh
git clone https://github.com/aws-samples/llm-app-genie.git
```

❗ **Automated deployment is implemented in 06_automation, go to this folder and proceed with other steps:**

```bash
cd llm-app-genie/06_automation
```

Change to the infrastructure as code directory and install the dependencies:

```bash
poetry install
poetry shell
```
Login with your AWS credentials. This step is not needed if you have already credentials loaded or if you are started Cloud9 with a user having all the required permissions.
```bash
aws configure
```
In Cloud9, when switching to a role different than the AWS managed default, remember to delete the file `~/.aws/credentials` first, then execute `aws configure`.


If required, you can change the used AWS account and region by setting the following env variables, 
```bash
export AWS_DEFAULT_REGION=<aws_region>
```
Also, you need to set the Account ID of the account to be used for deployment:
```bash
export CDK_DEFAULT_ACCOUNT=<your_account_id>
```

You can review the [CDK Deployment Flow](https://github.com/aws/aws-cdk/wiki/Security-And-Safety-Dev-Guide#:~:text=expects%20to%20exist.-,Deployment%20Flow,-This%20guide%20will) to understand what roles and access rights for each role are being used.
In a nutshell, you can bootstrap CDK (`cdk boostrap`) using e.g. credentials with Administrator access, which creates a set of scoped roles (`cdk-file-publishing-role, cdk-image-publishing-role, cdk-deploy-role, cdk-exec-role`).
```bash
cdk bootstrap
```

You can trigger the deployment through CDK which assumes the file, image publishing and deployment role to initiate the deployment through AWS CloudFormation which then can use the passed `cdk-exec-role` IAM role to create the required resources.

Note that the deployment user does not need to have the rights to directly create the resources.

### Fast, minimal, fully managed Deployment <a name="minimal-deployment"> </a>

If you want a minimal deployment using fully managed AWS services, you can follow these instructions. You need to deploy:

1. A knowledge base (KB) with a search index over ingested documents based on Amazon Kendra. 
2. A Chatbot front-end which orchestrates the conversation with langchain, using Large Language Models available in Amazon Bedrock.

**Step 1: Deploying the knowledge base on Amazon Kendra**

To deploy the Kendra index and data sources, follow the instructions in [Deploying Amazon Kendra](./06_automation/stacks/README.md#deploying-amazon-kendra)

```bash
cdk deploy GenieKendraIndexStack GenieKendraDataSourcesStack --require-approval never
```

`KendraIndexStack` creates an Amazon Kendra Index and a `WEBCRAWLERV2` data source pointing at the website you specified in the [app config](06_automation/configs/dev.json). The default configuration points to the last 10 pages of [media releases from the federal website admin.ch.](https://www.admin.ch/gov/en/start/documentation/media-releases.html)

The stack deployment takes about 30 minutes.

**Step 2: Deploy the chatbot based on Amazon Bedrock LLMs**

Before to deploy the chatbot you need to decide whether update the Amazon Bedrock region in the [deployment config](./06_automation/configs/dev.json#L8), setup by default to `us-west-2`.
You can check more information in the **Amazon Bedrock** section in [03_chatbot/README.md](./03_chatbot/README.md#amazon-bedrock). 

❗ **When using Amazon Bedrock remember that although the service is now Generally Available, the models need to be activated in the console.**

```bash
cdk deploy GenieChatBotStack --require-approval never
```
The deployment should take 10 minutes.

The link to access the chatbot can be found in the CloudFormation Output variables for the stack, in the region used for the deployment.

Since the chatbot is exposed to the public internet, the UI interface is protected by a login form. The credentials are automatically generated and stored in AWS Secret Manager.
The Streamlit credentials can be retrieved either by navigating in the console to the AWS Secret Manager, or by using the AWS CLI.

```bash
# username
aws secretsmanager get-secret-value --secret-id GenieStreamlitCredentials | jq -r '.SecretString' | jq -r '.username'
# password
aws secretsmanager get-secret-value --secret-id GenieStreamlitCredentials | jq -r '.SecretString' | jq -r '.password'
```

When connecting to the website, you will see a self-signed certificate error from the browser. You can ignore the error and proceed to the website.


### Fully modular Deployment: Deploying individual components of choice <a name="modular-deployment"> </a>

You can also deploy individual components only. Genie will automatically detect which components are available based on resource tags (defined in [deployment config](./06_automation/configs/dev.json)) and use them accordingly. Check [automation readme](./06_automation/README.md) for more details.

The Genie components are:

1. A large language model (LLM).
2. A knowledge base (KB) with a search index over ingested documents. Genie queries the KB and uses returned documents to enhance the LLM prompt and provide document links in the response. Amazon Kendra or Amazon OpenSearch are the knowledge base and provide the search capabilities
3. A Chatbot front-end which orchestrates the conversation with langchain.
4. Amazon SageMaker Studio domain for experimentation

❗ **Genie is default application Prefix, if case you change it make sure to modify the commands below**

**Step 1: Deploying the LLM**  
The solution deploys by default the [Falcon 40b instruct](https://huggingface.co/tiiuae/falcon-40b-instruct) LLM.

```bash
cdk deploy GenieLlmPipelineStack --require-approval never
```

After the deployment is completed, you can navigate to AWS CodePipeline to monitor how the deployment is proceeding (it takes between 10 and 15 minutes).

**Step 2: Deploying the knowledge base**

To deploy the Amazon OpenSearch index, follow the instructions below.

```bash
cdk deploy GeniePrivateOpenSearchDomainStack GenieOpenSearchVPCEndpointStack GeniePrivateOpenSearchIngestionPipelineStack --require-approval never
```

`GenieOpenSearchDomainStack` deploys an OpenSearch domain inside its own VPC, protected by an IAM role.
The `GenieOpenSearchVPCEndpointStack` stack deploys a VPC endpoint for private network traffic between the chatbot and the OpenSearch cluster.
You can optionally deploy `GeniePrivateOpenSearchIngestionPipelineStack`, which initiates the pipeline that creates a SageMaker real-time endpoint for computing embeddings, and a custom crawler to download the website defined in the [`admin-ch-press-releases-en.json`](01_crawler/crawly/configs/admin-ch-press-releases-en.json). It also ingests the documents downloaded by the crawler into the OpenSearch domain.

To deploy the Kendra index and data sources, follow the instructions in [Deploying Amazon Kendra](./06_automation/stacks/README.md#deploying-amazon-kendra)

```bash
cdk deploy GenieKendraIndexStack GenieKendraDataSourcesStack --require-approval never
```

`KendraIndexStack` creates an Amazon Kendra Index and a `WEBCRAWLERV2` data source pointing at the website you specified in the [app config](06_automation/configs/dev.json).
The stack deployment takes about 30 minutes. The crawling and ingestion pipeline can take longer depending on the size of the website, amount of downloaded documents, and the crawler depth you specified.

**Step 3: Deploy the chatbot**

The chatbot requires the following configuration:

- the Sagemaker endpoint name for the embeddings
- the SageMaker endpoint name for the LLM
- the endpoint for the OpenSearch domain
- the index of the OpenSearch to query
- the Kendra index ID

[Optional] Use chatbot with Amazon Bedrock:

- Before to deploy the chatbot you need to decide whether update the Amazon Bedrock region in the [deployment config](./06_automation/configs/dev.json#L8), setup by default to `us-west-2`.
You can check more information in the **Amazon Bedrock** section in [03_chatbot/README.md](./03_chatbot/README.md#amazon-bedrock). 

❗ **When using Amazon Bedrock remember that although the service is now Generally Available, the models need to be activated in the console.**


These configurations are identified by specific resource tags deployed alongside the resources.
The chatbot dynamically detects the available resources based on these tags.
If you want to personalize the chatbot icons, you can do so by updating the configuration in the [./03_chatbot/chatbot/appconfig.json](03_chatbot/chatbot/appconfig.json) file.

```bash
cdk deploy GenieChatBotStack --require-approval never
```

The chatbot UI interface is protected by a login form. The credentials are automatically generated and stored in AWS Secret Manager.
The Streamlit credentials can be retrieved either by navigating in the console to the AWS Secret Manager, or by using the AWS CLI.

```bash
# username
aws secretsmanager get-secret-value --secret-id GenieStreamlitCredentials | jq -r '.SecretString' | jq -r '.username'
# password
aws secretsmanager get-secret-value --secret-id GenieStreamlitCredentials | jq -r '.SecretString' | jq -r '.password'
```

By default, we deploy a self-signed certificate to enable encrypted communication between the browser and the chatbot.
The default configuration of the self-signed certificate can be found in [dev.json](./06_automation/configs/dev.json):

```json
{
  ...
  "self_signed_certificate": {
    "email_address": "customer@example.com",
    "common_name": "example.com",
    "city": ".",
    "state": ".",
    "country_code": "AT",
    "organization": ".",
    "organizational_unit": ".",
    "validity_seconds": 157680000 # 5 years validity
  }
}
```

To avoid the self-signed certificate error from the browser, we recommend to deploy your own certificate to the chatbot.
You can import your own certificate to Amazon Certificate Manager, or generate a new one if you have a domain registered into Route 53 and point it to the Application Load Balancer of the Chatbot.

**Step 4: Deploy Sagemaker Studio Domain**
Amazon SageMaker Studio provides an environment where you experiment in the notebooks with different LLMs, embeddings, and fine-tuning.

The solution provides notebooks for experimentation. For example:

- [./00_llm_endpoint_setup/deploy_embeddings_model_sagemaker_endpoint.ipynb](./00_llm_endpoint_setup/deploy_embeddings_model_sagemaker_endpoint.ipynb) to deploy a SageMaker endpoint to help create document embeddings with HuggingFace's Transformers.
- [./00_llm_endpoint_setup/deploy_falcon-40b-instruct.ipynb](./00_llm_endpoint_setup/deploy_falcon-40b-instruct.ipynb) to deploy Falcon 40b Foundation Model, either real-time or asynchronous.

```bash
cdk deploy SageMakerStudioDomainStack --require-approval never
```

### Full deployment <a name="full-deployment"></a>

You can deploy all the components (stacks) of the solution at once.

❗ **By default, this solution deploys the Falcon 40B LLM model on a `ml.g5.12xlarge` compute instance on Amazon SageMaker. Please ensure your account has an appropriate service quotas for this type of instance in the AWS region you want to deploy the solution. Alternatively you can [enable your favorite models in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html), in your preferred region.**

The simplest way is to use Launch Stack (to be added), which uses a AWS CloudFormation template to bootstrap an AWS CodeCommit repo from the GitHub repository and triggers a full deployment using AWS CodePipeline.

Alternatively, you can use the next steps to deploy the full solution with CDK.

**Step 1:** Deploying with CDK

Make sure your current working directory is `06_automation`.
The following command will check for available stack and deploy the whole solution.
CDK will add the Application Prefix to all stack (**Genie** by default)

```bash
cdk ls
cdk deploy GenieDeploymentPipelineStack GenieLlmPipelineStack GenieKendraIndexStack GenieKendraDataSourcesStack GenieChatBotStack GeniePrivateOpenSearchDomainStack GenieOpenSearchVPCEndpointStack GeniePrivateOpenSearchIngestionPipelineStack --require-approval never
```

The most relevant app configuration parameters are being loaded from the [deployment config](./06_automation/configs/dev.json)


### CI/CD Deployment

We provide an alternative way to deploy the solution by setting up a CI/CD pipeline on your AWS account.
We first deploy the infrastructure to for the deployment.
We use:
1. AWS CodeCommit to host the git repo
2. AWS CodeBuild to deploy the full solution via cdk
3. AWS CodePipeline to orchestrate the deployment

In the default settings, the pipeline will trigger only for the `develop` branch, but this can be changed.

```Bash
cd <path-to-cloned-repo>/06_automation
cdk deploy GenieDeploymentPipelineStack --require-approval never
```

You can configure your git to authenticate against AWS CodeCommit using your AWS credentials.
See [here](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-git-remote-codecommit.html) for more information

```Bash
cd <path-to-cloned-repo>/
pip install git-remote-codecommit
git remote set-url origin codecommit://Genie-repo
git push
```

### Common Deployment Scenarios <a name="common-deployment-scenarios"></a>

The solution is flexible and will [automatically discover the available resources](./03_chatbot/README.md#discovery-of-available-knowledge-bases-and-llms), including Amazon Bedrock models, knowledge bases (Amazon Kendra and Amazon OpenSearch), and available LLM endpoints.
This means you can decide which knowledge base you combine with which LLM. 
If you do not have access to Amazon Bedrock, or if it is not available in the AWS Region of your choice, you need to deploy an LLM on Amazon SageMaker.

The most common scenarios are:

- Amazon Kendra + Large LLM on Amazon Bedrock (Claude v2 100K)
- Amazon Kendra + Large LLM on Amazon SageMaker (Falcon 40B)
- Amazon OpenSearch + Large LLM on Amazon Bedrock (Claude Instant 12K)
- Amazon OpenSearch + Light LLM on Amazon SageMaker (Falcon 7B)

## I need help <a name="i-need-help"></a>

If you want to report a bug please open an issue in this repository with the _Default bug_ issue template.
Would you like to request a new feature then please open an issue with the _Feature Request_ template.

In case you have a general question or simply need help please open an issue with the _I need Help_ issue template so that we can get in touch with you.

## Usage Scenarios <a name="usage-scenarios"></a>

### How to populate knowledge bases ? <a name="populate-knowledgebase"></a>

You can add knowledge (textual content) by ingesting it to the available knowledge bases.

The main options are:

1. Add additional data sources to Amazon Kendra and run the ingestion
2. Manually add knowledge to Amazon OpenSearch by

- [running the crawler](01_crawler/README.md) and
- [ingesting crawling results](02_ingestion/04_ingest_html_embeddings_to_opensearch.ipynb)

3. Retrigger the ingestion pipeline by changing the CodeCommit repo created by the `GenieOpenSearchIngestionPipelineStack`.

### How to fine-tune a LLM? <a name="finetune"></a>

An example of LLM fine-tuning is provided in 2 steps for the model Falcon 40B, i.e. the [actual tuning](./04_finetuning/train_llms_with_qlora/fine-tune-falcon.ipynb) and the [deployment of the tuned model](./04_finetuning/deploy_llms_with_qlora/deploy_fine_tuned_falcon.ipynb). 

The fine-tuning is performed using QLoRA, a technique that quantizes a model to 4 bits while keeping the performance of full-precision. This technique enables models with up to 65 billion parameters on a single GPU and achieves state-of-the-art results on language tasks.

The deployment is done using the Hugging Face Text Generation Inference Container (TGI), which enables high-performance using Tensor Parallelism and dynamic batching.

### How to customize the chatbot? <a name="customize-chatbot"></a>

If you want to dive deeper beyond the default configuration of the chatbot please read the [03_chatbot/README.md](/03_chatbot/README.md).

## Costs and Clean up <a name="costs-and-clean-up"> </a>

### Costs <a name="costs"> </a>

This solution is going to generate costs on your AWS account, depending on the used modules.
The main cost drivers are expected to be the real-time Amazon SageMaker endpoints and the knowledge base (e.g. Amazon OpenSearch Service, Amazon Kendra), as these services will be always up and running. 

Amazon SageMaker endpoints can host the LLM for text generation, as well as the embeddings model used in combination with Amazon OpenSearch. Their pricing model is based on instance type, number of instances, and time running (billed per second). The default configuration uses (pricing in USD for the Ireland AWS Region as of September 2023):
  - 1 x ml.g5.12xlarge for the LLM ($7.91/hour)
  - 1 x ml.g4dn.xlarge for the embeddings ($0.821/hour)

Note that extra cost may apply when using commercial models through the AWS Marketplace (e.g.: AI21 Labs LLM models).

You can delete the Amazon SageMaker endpoints during non-working hours to pause the cost for the LLM running on the Amazon SageMaker endpoint, or use Asynchronous endpoints. For a pay-per-token pricing model use Amazon Bedrock which bills the number of input and output tokens. This means that, if you do not use the application, there is no cost from the LLM.

With regards to the knowledge bases, you can choose between Amazon Kendra and Amazon OpenSearch Service. [Amazon Kendra pricing model](https://docs.aws.amazon.com/whitepapers/latest/how-aws-pricing-works/amazon-kendra.html) depends on the edition you choose (Developer or Enterprise). The Developer Edition is limited to a maximum of 10,000 documents, 4,000 queries per day, and 5 data sources. If you need more than that or you are running in production you should use the Enterprise Edition.

Amazon OpenSearch Service pricing is based on instance type, number of instances, time running (billed per second), and EBS storage attached. The default configuration uses a single node cluster with 1 x t3.medium.search instance and 100 GB EBS storage (gp2).

Finally, the application relies on an Amazon ECS task running on AWS Fargate and on an Amazon DynamoDB table. AWS Fargate pricing model is based on requested vCPU, memory, and CPU architecture, and billed per second. The default configuration uses 1 vCPU and 2 GB of memory, and uses Linux/x86_64 architecture. The default solution provisions a DynamoDB Standard table with on-demand capacity. DynamoDB pricing dimensions include read and write request units and storage.

Pricing examples of LLM and knowledge base for four scenarios (prices in USD for Ireland AWS Region as of September 2023):

**Amazon Bedrock + Amazon Kendra**
  - See Amazon Bedrock console for model pricing
  - Amazon Kendra Developer Edition: **$810/month**
  - **Monthly total = $810 + Amazon Bedrock cost**

**Work hours Large LLM on Amazon SageMaker + Amazon OpenSearch**
  - Real-time endpoints, 8 hours/day, 20 days/month = 160 hours/month.
  - Endpoint for LLM on 1 x ml.g5.12xlarge: $7.91 x 160 = **$1265.6**
  - Endpoint for embeddings on 1 x ml.g4dn.xlarge: $0.821 x 160 = **$131.36**
  - Amazon OpenSearch Service: t3.medium.search + 100 GB EBS (gp2) = 720 h/month x $0.078/hour + $0.11 GB/hour * 100 GB = **$67.16**
  - **Monthly total = $1265.6 + $131.36 + $67.16 = $1464.12**

**Work hours Large LLM on Amazon SageMaker + Amazon Kendra**
  - Real-time endpoint based on 1 x ml.g5.12xlarge, 8 hours/day, 20 days/month: $7.91 x 8 x 20 = **$1265.6**
  - Amazon Kendra Developer Edition: **$810**
  - Monthly total = $810 + $1265.6 = **$2093.7457**

**Always-on light LLM on Amazon SageMaker + Amazon Kendra**
  - Real-time endpoint based on 1 x ml.g5.4xlarge, 24/7 (720 hours/month): $2.27 x 720 = **$1634.4**
  - Amazon Kendra Developer Edition: **$810**
  - **Monthly total = $810 + $1634.4  = $2462.5457**


| Item                               |                                     Description                                     | Monthly Costs |
| :--------------------------------- | :---------------------------------------------------------------------------------: | ------------: |
| Knowledge Base - Amazon Kendra     |  Developer Edition (maximum of 10,000 documents, 4,000 queries per day, and 5 data sources)      |  810.00 USD  |
| Knowledge Base - Amazon OpenSearch | 1 x ml.g4dn.xlarge for embeddings pluc 1 x t3.medium.search instance with 100 GB EBS storage (gp2) |  198.52 USD |
| Full LLM (Falcon 40B)              | ml.g5.12xlarge (CPU:48, 192 GiB, GPU: 4),<br> 8 hours/day x 20 days x 7.09 USD/hour |  1,134.40 USD |
| Light LLM (Falcon 7B)              |  ml.g5.4xlarge (CPU:16, 64 GiB, GPU: 1),<br> 8 hours/day x 20 days x 2.03 USD/hour  |    324.80 USD |

### Clean up <a name="clean-up"> </a>

To clean up the resources, first you need to delete the SageMaker endpoints created by the two AWS CodePipeline pipelines since they are not managed by CDK.

```bash
aws cloudformation delete-stack --stack-name GenieLLMSageMakerDeployment
aws cloudformation delete-stack --stack-name GenieEmbeddingsSageMakerDeployment
```

Then, you can remove the stacks created by CDK

```bash
cdk destroy --all
```

Some resources use the CDK [`RemovalPolicy.RETAIN`](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/RemovalPolicy.html#aws_cdk.RemovalPolicy.RETAIN). Those resources do not get delete to not accidentally delete important data. They may cause the deletion to fail and you need to delete the resources manually. Here are the resources with `RemovalPolicy.RETAIN`:

| Stack                               |                                     Resource                                     | 
| :--------------------------------- | :---------------------------------------------------------------------------------: | 
| Nested *OpenSearchDomainStack-ChatbotAccessLogsStack    |  OpenSearch Domain      | 
| Nested *ChatBotStack-ChatbotAccessLogsStack    |  S3 bucket access logs bucket      | 
| Nested *DeploymentPipelineStack-ChatbotAccessLogsStack    |  S3 bucket access logs bucket      | 
| Nested *LlmPipelineStack-ChatbotAccessLogsStack    |  S3 bucket access logs bucket      | 
| Nested *OpenSearchIngestionPipelineStack-ChatbotAccessLogsStack    |  S3 bucket access logs bucket      | 


## Setup development environment<a name="setup-development-environment"></a>

Below you can see the repository structure. We use different environments for each component.
You should follow the [local development guide](#local-development-guide), if you want to provide a pull request.

- How to setup the development environment for the chatbot? <br> Follow the [chatbot Readme](./03_chatbot/README.md).
- How to setup the development environment for the automation project? <br>Follow the [Full Deployment section](#full-deployment).

### Pull Requests <a name="pull-requests"></a>

We appreciate your collaboration because it is key to success and synergies. However, we want to make sure that the contributions can be maintained in the future, thus create an issue with the proposed improvements and get feedback before you put in the effort to implement the change.

If you want to contribute a bug fix please use the _Default pull_ request template.

### Repository structure <a name="repo_structure"></a>

1. [00_llm_endpoint_setup](./00_llm_endpoint_setup)
   - Embedding endpoint setup
   - LLM endpoint setup
2. [01_crawler](./01_crawler)
   - Web crawler which downloads content from a public or private web page recursively using `playwright` and [Mozilla's `readability.js` plugin](https://github.com/mozilla/readability). For more details see the [README](./01_crawler/README.md)
3. [02_ingestion](./02_ingestion)
   - Split and Ingestion of the downloaded webpage paragraphs into a vector store (OpenSearch) using semantic embeddings.
4. [03_chatbot](./03_chatbot)
   - Chatbot application based on Streamlit and Langchain
5. [04_finetuning](./04_finetuning)
   - LLM fine-tuning pipelines
6. [05_doc](./05_doc)
   - Solution documentation
7. [06_automation](./06_automation)
   - Infrastructure as code (CDK)

### Local Development Guide <a name="local-development-guide"> </a>

In preparation

### Pre-requisites for Development <a name="pre-requisites-for-development"> </a>

We use Trunk for security scans, code quality, and formatting. If you plan to contribute to this repository please install Trunk.

**Step 1:** Install Trunk

To use `trunk` locally, run:

If you are on MacOS run:

```bash
brew install trunk-io
```

or you are on a different OS or not using Homebrew run:

```bash
curl https://get.trunk.io -fsSL | bash
```

For other installation options and details on exactly Trunk install or how to uninstall, see the [Install Trunk](https://docs.trunk.io/docs/install) doc.

**Step 2:** Initialize Trunk in a git repo

From the root of a git repo, run:

```bash
trunk init
```

See also https://github.com/trunk-io/ for additional information on trunk.

## Troubleshooting/FAQ <a name="troubleshootingfaq"> </a>

In preparation

## Bump a new version

We track in code the current released version in [03_chatbot/pyproject.toml](03_chatbot/poetry.lock).
When releasing a new version, ensure you create a git commit and a git tag to easily identify the bumped file.
You can do this with the following command:

```Bash
pip install bump-my-version
bump-my-version bump patch/minor/major 03_chatbot/pyproject.toml --commit --tag
```

Then push the commit and tag:
```Bash
git push && git push <your-upstream-repo> <tagname>
```

## Copyright information <a name="copyright"> </a>

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
