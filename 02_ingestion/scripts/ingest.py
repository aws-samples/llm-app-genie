# automate script
import json
import os
import re

import awswrangler as wr
import boto3
import pandas as pd
import sagemaker
from bs4 import BeautifulSoup
from langchain.schema import Document
from langchain.vectorstores import OpenSearchVectorSearch
from sagemaker.huggingface.model import HuggingFacePredictor

sess = sagemaker.Session()
region = sess.boto_region_name
ssm_client = boto3.client("ssm")

secret_name = os.getenv("OPENSEARCH_SECRET_NAME")
os_domain_name = os.getenv("OPENSEARCH_DOMAIN_NAME")
os_index_name = os.getenv("OPENSEARCH_INDEX_NAME")
hf_predictor_endpoint_name = os.getenv('ENDPOINT_NAME')
#TODO: find a better way to app app specific prefix
app_prefix = os.getenv("APP_PREFIX")

def get_credentials(secret_id: str, region_name: str) -> str:
    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_id)
    secrets_value = json.loads(response["SecretString"])
    return secrets_value

credentials = get_credentials(secret_name, region)
user = credentials["user"]
secret = credentials["password"]

os_http_auth = (user, secret)

print(f"opensearch domain name: {os_domain_name}")

os_domain_ep = ssm_client.get_parameter(Name=f"{app_prefix}OpenSearchEndpoint")["Parameter"][
    "Value"
]
print(f"opensearch domain endpoint: {os_domain_ep}")

# Get data
crawled_file_path = ssm_client.get_parameter(Name=f"{app_prefix}CrawledFileLocation")["Parameter"][
    "Value"
]
df = pd.read_json(crawled_file_path)

#df.style.set_properties(**{"text-align": "left"})

df.head()


def convert_paragraphs(row):
    html = row["content"]
    textContent = row["textContent"]
    soup = BeautifulSoup(html, features="html.parser")
    sections = [h.text for h in soup.find_all(re.compile("^h[1-6]$"))]
    paragraphs = []
    pos = 0
    for section in sections:
        split_pos = textContent.find(section, pos, len(textContent))
        paragraphs.append(textContent[pos:split_pos])
        pos = split_pos
    paragraphs.append(textContent[pos : len(textContent)])

    paragraphs_clean = [p.strip() for p in paragraphs if len(p.strip()) > 0]
    return paragraphs_clean


paragraphs = df.apply(convert_paragraphs, axis=1)
df["paragraphs"] = paragraphs.tolist()

# store df
df.to_json("pages_with_paragraphs_clean_by_section.json")

df_skus = df[["title", "paragraphs"]].explode("paragraphs")

predictor = HuggingFacePredictor(endpoint_name=hf_predictor_endpoint_name)


class CustomEmbeddings:
    def __init__(self, embeddings_predictor):
        self.embeddings_predictor = embeddings_predictor

    def embed_documents(self, input_texts):
        return self._embed_docs(input_texts, False)

    def embed_query(self, query_text):
        return self._embed_docs([query_text])[0]

    def _embed_docs(self, texts, isQuery=False):
        data = {
            "texts": texts,
        }

        res = self.embeddings_predictor.predict(data=data)
        return res["vectors"]


docs = []
for index, row in df.iterrows():
    for par_num, paragraph in enumerate(row["paragraphs"]):
        meta = {"source": row["source"], "title": row["title"]}
        doc = Document(page_content=paragraph, metadata=meta)
        docs.append(doc)
len(docs)

# Delete existing index
try:
    client = wr.opensearch.connect(host=os_domain_ep, username=user, password=secret)
    wr.opensearch.delete_index(client=client, index=os_index_name)
except:
    print(f"failed to delete index {os_index_name}")

custom_embeddings = CustomEmbeddings(predictor)
docsearch = OpenSearchVectorSearch(
    index_name=os_index_name,
    embedding_function=custom_embeddings,
    opensearch_url=os_domain_ep,
    http_auth=os_http_auth,
    use_ssl=True,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
)
print(len(docs))

# adding document to open search index with progress bar
for doc in docs:
    docsearch.add_documents(documents=[doc])
