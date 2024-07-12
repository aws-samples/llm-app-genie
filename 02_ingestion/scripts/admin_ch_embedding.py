import os
import pandas as pd
from modules.embedding import convert_paragraphs, generate_embeddings
from modules.opensearch_helpers import opensearch_auth, embeddings_to_index
from modules.aws_helpers import get_parameter_value

app_prefix = os.getenv("APP_PREFIX")
secret_name = os.getenv("OPENSEARCH_SECRET_NAME")
os_index_name = os.getenv("OPENSEARCH_INDEX_NAME")
os_domain_ep = get_parameter_value(f"{app_prefix}OpenSearchEndpoint")

print(f"opensearch domain endpoint: {os_domain_ep}")

# Get data
crawled_file_path = get_parameter_value(f"{app_prefix}CrawledFileLocation")
df = pd.read_json(crawled_file_path)

paragraphs = df.apply(convert_paragraphs, axis=1)
df["paragraphs"] = paragraphs.tolist()

df.to_json("pages_with_paragraphs_clean_by_section.json")

docs = generate_embeddings(df)
os_http_auth = opensearch_auth(os_domain_ep, secret_name)

if os.getenv("EMBEDDING_TYPE") == "Sagemaker":
    huggingface_config = {
        "predictor_endpoint_name": os.getenv('ENDPOINT_NAME')
    }
    embeddings_to_index(os_domain_ep, os_index_name, docs, os_http_auth, bedrock_config=huggingface_config)
else:
    bedrock_config = {
        "region": os.getenv("BEDROCK_REGION"),
        "model_id": os.getenv("BEDROCK_EMBEDDING_MODEL")
    }
    embeddings_to_index(os_domain_ep, os_index_name, docs, os_http_auth, bedrock_config=bedrock_config)



