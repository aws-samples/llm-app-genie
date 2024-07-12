import os
from modules.aws_helpers import get_parameter_value, read_from_s3, s3_client
import pandas as pd
from langchain.schema import Document
from modules.opensearch_helpers import opensearch_auth, embeddings_to_index


# Parameter group Finance Analyzer
s3_bucket = os.getenv("S3_BUCKET")
s3_prefix = os.getenv("S3_PREFIX")

app_prefix = os.getenv("APP_PREFIX")
secret_name = os.getenv("OPENSEARCH_SECRET_NAME")
os_index_name = os.getenv("OPENSEARCH_INDEX_NAME")
os_domain_ep = get_parameter_value(f"{app_prefix}OpenSearchEndpoint")

if s3_bucket == "" or os_index_name == "":
    print("Complete Fin Analyzer setup. Please provide S3_BUCKET and OPENSEARCH_INDEX_NAME environment variables")
    exit(0)

os_http_auth = opensearch_auth(os_domain_ep, secret_name)

print(f"opensearch domain endpoint: {os_domain_ep}")

df = pd.read_json(f"s3://{s3_bucket}/{s3_prefix}/embedding_docs.json")
docs = [Document(page_content=row["page_content"], metadata=row["metadata"]) for _, row in df.iterrows()]

if os.getenv("EMBEDDING_TYPE") == "Sagemaker":
    huggingface_config = {
        "predictor_endpoint_name": os.getenv('ENDPOINT_NAME')
    }
    embeddings_to_index(os_domain_ep, os_index_name, docs, os_http_auth, huggingface_config=huggingface_config)
else:
    bedrock_config = {
        "region": os.getenv("BEDROCK_REGION"),
        "model_id": os.getenv("BEDROCK_EMBEDDING_MODEL")
    }
    embeddings_to_index(os_domain_ep, os_index_name, docs, os_http_auth, bedrock_config=bedrock_config)
