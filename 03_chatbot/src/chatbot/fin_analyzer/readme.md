# Finance Analyzer Application Mode

- [Finance Analyzer Application Mode](#finance-analyzer-application-mode)
  - [Introduction](#introduction)
  - [Crawl the finance data](#crawl-the-finance-data)
  - [Update Genie application config](#update-genie-application-config)
  - [Optional: Embed the Finance data into OpenSearch index](#optional-embed-the-finance-data-into-opensearch-index)
  - [Check the prompt hints](#check-the-prompt-hints)

## Introduction

This is special application mode to include Finance Analyzer functionality into standard Genie application.

This mode allows you to analyze latest finance documents (SEC fillings) of top US market companies with flexible setup to explore 2 modes:
- **File mode** - data will be loaded from directly from Amazon S3 for analysis
- **Retrieval Augmented Generation (RAG)** - data will be loaded to Vector store (Open Search) for further analysis


## Crawl the finance data

In order to crawl the finance data below steps are required:

1. Get API keys from [Finnhub (financial data API)](https://finnhub.io/) and [Alpaca (daily prices API)](https://alpaca.markets/), both providers have free tiers
2. Create a new secret in AWS Secrets Manager, select type as **Other type of secret** and add your keys as follows:

| Secret key          | Secret value  |
| --------            | --------      |
| finnhub_api_key     | ******        |
| apca_api_key_id     | ******        |
| apca_api_secret_key | ******        |

3. Make sure you have access to the secret. Open [python file](../../../../02_ingestion/scripts/fin_analyzer_data.py) and update below line with your secret name:

```python
secret_name = "GenieFinAnalyzerAPIs"
```

4. In the same file update the Amazon S3 destination:

```python
# S3 bucket and prefix for market data
s3_bucket = "your_bucket_name"
s3_prefix = "finance-analyzer"
```

5. Optionally, update the required data sources and document types:

```python
data_sources=[
    {"ticker": "AMZN"}, 
    {"ticker": "GOOGL"}, 
    {"ticker": "NFLX"}, 
    {"ticker": "TSLA"}, 
    {"ticker": "AAPL"}
]

document_types=[
    "10-K",     # Annual report filed by public companies. Provides comprehensive summary of company's performance. Contains audited financial statements.
    "10-Q",     # Quarterly report filed by public companies. Provides unaudited financial statements and update on operations. 
    # # Skipping 8-K for now, as it often references other documents without substantial standalone information
    # "8-K",    # Report on material events or corporate changes which is filed as needed. Used to announce major events like mergers, CEO change, bankruptcy.
    "DEF 14A",  # Definitive proxy statement which details information for shareholders ahead of annual shareholder meeting.
    "13F-HR",   # Required quarterly filing by institutional investment managers detailing their equity holdings. 
    "4"         # Insider trading filing showing stock purchases/sales by corporate insiders.
]
```
5. Make sure you have required libraries, this is special mod, so the modules are not included in standard poetry setup:
```bash
pip install requests fake_useragent markdownify finnhub-python alpaca_trade_api defusedxml
```
6. Go inside **02_ingestion** folder and execute the file and check that the files are uploaded to S3

```bash
cd 02_ingestion 
python -m scripts/fin_analyzer_data
```

## Update Genie application config

Update [appconfig.json](../appconfig.json) with below setup, example config could also be found in [fin_analyzer_appconfig.json](../../../example_app_configs/fin_analyzer_appconfig.json)

1. Replace or update below lines with Finance Analyzer prompts
```json
  "llmConfig": {
    "parameters": {
      "anthropic\\.claude.*": {
        "type": "LLMConfig",
        "parameters": {
          "chatPrompt": "prompts/fin_analyzer_anthropic_claude_chat.yaml",
          "ragPrompt": "prompts/fin_analyzer_anthropic_claude_rag.yaml"
        }
      }
    },
    "type": "LLMConfigMap"
  },

``` 

2. Add data and menu related setup
```json
  "finAnalyzer": {
    "type": "FinAnalyzer",
    "parameters": {
      "friendlyName": "The name in the Genie menu", 
      "s3Bucket": "your S3 bucket",
      "s3Prefix": "finance-analyzer"
    }
  }

```

## Optional: Embed the Finance data into OpenSearch index

If you also want to activate the RAG mode with OpenSearch you need to embed the data you crawled into OpenSearch domain. 
**Make sure you deployed the CDK Open Search stack.**

Open [Jupyter Notebook file](../../../../02_ingestion/50_ingest_stock_embeddings_to_opensearch.ipynb) and follow the instruction.

## Check the prompt hints
If you updated the friendlyName or would like to customize the prompt button, check the [prompt hints](../prompts/hints.yaml):
```yaml
Retrieval Augmented Generation:
  Stock Analysis: # this is friendlyName you provided in appconfig.json file
    all:
      - name: Key financial information
        prompt: "Give detailed key financial information for each announcement, split the highlights and lowlights #graph"
      - name: Risks in table format (German)
        prompt: Highlight all the risks for each announcement in table format, give this information in German
      - name: Impact with price targets
        prompt: "Provide an analytical conclusion based on the data provided. Summarize if the announcement had a positive or negative impact and any patterns or trends observed #graph"
      - name: Comparison with buy/sell/hold
        prompt: "Make the detailed comparison for provided announcements, recommend buy/sell/hold actions, assume the most probable scenario, also what in your opinion will be a price in 6, 12 and 24 month for each company. Put all the details into table #graph"
  OpenSearch Domain - Demo:
    stock-market: # this is OpenSearch index name from Jupyter Notebook
      - name: Latest AAPL 10-Q announcement
        prompt: Summarize in table format AAPL 10-K announcement from 1st of July 2023
      - name: 10-Q comparison with buy/sell/hold action
        prompt: Compare Latest 10-Q report of AMZN, AAPL and GOOG. Make the comparison in table format, include buy/hold/sell recommendation and price forecast for the next 6, 12 and 24 months
      - name: AMZN announcements analysis
        prompt: Make the detailed analysis in table format for latest AMZN announcements, recommend buy/sell/hold actions, assume the most probable scenario, also what in your opinion will be a price in 6, 12 and 24 month for each company
```
