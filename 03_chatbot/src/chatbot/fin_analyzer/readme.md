# Finance Analyzer Application Mode

- [Finance Analyzer Application Mode](#finance-analyzer-application-mode)
  - [Introduction](#introduction)
  - [Crawl the finance data](#crawl-the-finance-data)
  - [Update Genie application config](#update-genie-application-config)
    - [File Mode](#file-mode)
    - [\[Optional\] Retrieval Augmented Generation (RAG): Embed the Finance data into OpenSearch index](#optional-retrieval-augmented-generation-rag-embed-the-finance-data-into-opensearch-index)

## Introduction

This is special application mode to include Finance Analyzer functionality into standard Genie application.

This mode allows you to analyze latest finance documents (SEC fillings) of top US market companies with flexible setup to explore 2 modes:
- **File mode** - data will be loaded from directly from Amazon S3 for analysis
- **Retrieval Augmented Generation (RAG)** - data will be loaded to Vector store (Open Search) for further analysis


## Crawl the finance data

In order to download the finance data below steps are required:

1. Get API keys from [Finnhub (financial data API)](https://finnhub.io/) and [Alpaca (daily prices API)](https://alpaca.markets/), both providers have free tiers
2. Complete [dev.json](../../../../06_automation/configs/dev.json) with corresponding API keys, email address is required to fill in the header for SEC download request:

```json
  "fin_analyzer": {
    "s3": {
      "prefix": "finance-analyzer"
    },
    "secret": {
      "finnhub_api_key": "******",
      "apca_api_key_id": "******",
      "apca_api_secret_key": "******",
      "user_agent_email": "your email address" 
    },
    "index": "stock-market"
  }

```

3. Open [fin_analyzer_data.py](../../../../02_ingestion/scripts/fin_analyzer_data.py) and update required datasources and documents types:

```python
data_sources=[
    {"ticker": "UBS"}, 
    {"ticker": "AMZN"}, 
    {"ticker": "GOOGL"}, 
    {"ticker": "AAPL"}
]

document_types=[
    "10-K",     # Annual report filed by public companies. Provides comprehensive summary of company's performance. Contains audited financial statements.
    "10-Q",     # Quarterly report filed by public companies. Provides unaudited financial statements and update on operations. 
    "11-K",      # Annual report filed by foreign companies.
    "6-K",      # REPORT OF FOREIGN PRIVATE ISSUER (UBS)
    # # Skipping 8-K for now, as it often references other documents without substantial standalone information
    # "8-K",    # Report on material events or corporate changes which is filed as needed. Used to announce major events like mergers, CEO change, bankruptcy.
    "DEF 14A",  # Definitive proxy statement which details information for shareholders ahead of annual shareholder meeting.
    "13F-HR",   # Required quarterly filing by institutional investment managers detailing their equity holdings. 
    # this is different file extension
    "4"         # Insider trading filing showing stock purchases/sales by corporate insiders.
]
```

## Update Genie application config
### File Mode
Update [appconfig.json](../appconfig.json) und update "Stock Analysis" node under "Retrieval Augmented Generation".
You can check and modify the prompts under stated pathes, as well as update hint buttons

```json
          "Stock Analysis": {
            "enabled": true,
            "friendlyName": "Stock Analysis",
            "rag": {
              "maxCharacterLimit": 50000,
              "retrievedDocumentsSlider": false
            },
            "prompts": {
              "anthropic\\.claude.*": {
                "chatPrompt": "fin_analyzer/prompts/anthropic_claude_chat.yaml",
                "ragPrompt": "fin_analyzer/prompts/anthropic_claude_rag.yaml"
              }
            },
            "hints": [
              {
                "name": "Key financial information",
                "prompt": "Give detailed key financial information for each announcement in table format, split the highlights and lowlights #graph"
              },
              {
                "name": "Risks in table format (German)",
                "prompt": "Highlight all the risks for each announcement in table format, give this information in German"
              },
              {
                "name": "Impact with price targets",
                "prompt": "Provide an analytical conclusion based on the data provided. Summarize if the announcement had a positive or negative impact and any patterns or trends observed #graph"
              },
              {
                "name": "Comparison with buy/sell/hold",
                "prompt": "Make the detailed comparison for provided announcements, recommend buy/sell/hold actions, assume the most probable scenario, also what in your opinion will be a price in 6, 12 and 24 month for each company. Put all the details into table #graph"
              }
            ]
          },

``` 

### [Optional] Retrieval Augmented Generation (RAG): Embed the Finance data into OpenSearch index
If you also want to activate the RAG mode with OpenSearch you need to embed the data you crawled into OpenSearch domain. 
**Make sure you deployed the CDK Open Search stack.**

Update [appconfig.json](../appconfig.json) und update "stock-market" (or your index name if you changed it above) node under "OpenSearch Domain - Demo" (or your name if you changed OpenSearch configuration).

```json
          "OpenSearch Domain - Demo": {
            "stock-market": {
              "embedding": {
                "type": "Bedrock",
                "model": "amazon.titan-embed-text-v2:0"
              },
              "prompts": {
                "anthropic\\.claude.*": {
                  "chatPrompt": "fin_analyzer/prompts/anthropic_claude_chat.yaml",
                  "ragPrompt": "fin_analyzer/prompts/anthropic_claude_rag.yaml"
                }
              },
              "rag": {
                "maxCharacterLimit": 10000,
                "retrievedDocumentsSlider": {
                  "minValue": 10,
                  "maxValue": 50,
                  "value": 30,
                  "step": 5
                }
              },
              "hints": [
                {
                  "name": "AMZN latest 10-Q analysis",
                  "prompt": "Make the detailed analysis for AMZN 10-Q announcements, recommend buy/sell/hold actions, also what in your opinion will be a price in 6, 12 and 24 month for the company"
                },
                {
                  "name": "AMZN current assets summary",
                  "prompt": "Compare Amazon.com Inc (AMZN) '10-Q' announcements current assets by group"
                },
                {
                  "name": "AAPL 10-K financials & forecast",
                  "prompt": "Provide detailed financials and risk analysis for AAPL 10-K announcement from 2023. Include buy/hold/sell recommendation and price forecast for the next 6, 12 and 24 months"
                },
                {
                  "name": "Amazon, Apple comparison",
                  "prompt": "Provide a detailed financial comparison table for Amazon (AMZN) and Apple (AAPL) based on their latest 10-Q announcements"
                }
              ]
            },
            "press-releases-en": {
              "hints": [
                {
                  "name": "Digital Vignette",
                  "prompt": "When Digital Vignette was announced in Switzerland?"
                },
                {
                  "name": "Ukraine support",
                  "prompt": "How Switzerland supports Ukraine?"
                },
                {
                  "name": "Kosovo news",
                  "prompt": "Latest news about Kosovo?"
                }
              ]
            }
          },
```
