import boto3
import awswrangler as wr
from langchain.vectorstores import OpenSearchVectorSearch
from sagemaker.huggingface.model import HuggingFacePredictor
from langchain.embeddings import BedrockEmbeddings
from opensearchpy import RequestsHttpConnection, AWSV4SignerAuth
from modules.embedding import CustomEmbeddings
from modules.aws_helpers import get_credentials
from tqdm import tqdm
from itertools import islice

# opensearch authentication
def opensearch_auth(os_domain_ep, secret_name = None):
    # checking for opensearch serverless version
    if ".aoss." in os_domain_ep:
        boto3_session = boto3.Session()

        credentials = boto3_session.get_credentials()    
        return AWSV4SignerAuth(credentials, boto3_session.region_name, "aoss")
    else:
        credentials = get_credentials(secret_name)
        user = credentials["user"]
        secret = credentials["password"]
        return (user, secret)

def chunked_iterable(iterable, size):
    iterator = iter(iterable)
    for first in iterator:
        yield [first] + list(islice(iterator, size - 1))

def embeddings_to_index(os_domain_ep, os_index_name, docs, os_http_auth, bedrock_config = None, huggingface_config = None):
    # Checking the authentication method
    if hasattr(os_http_auth, "service"):
        user = None
        secret = None
    else:
        user, secret = os_http_auth

    try:
        client = wr.opensearch.connect(host=os_domain_ep.replace(":443", ""), username=user, password=secret)
        wr.opensearch.delete_index(client=client, index=os_index_name)
        print(f"index {os_index_name} is deleted")
    except Exception as err:
        print(f"failed to delete index {os_index_name} with error: {err}")

    if huggingface_config:
        # HuggingFace custom predictor
        predictor = HuggingFacePredictor(endpoint_name=huggingface_config["predictor_endpoint_name"])
        embeddings = CustomEmbeddings(predictor)
        embedding_provider = "huggingface"
    elif bedrock_config:
        # Bedrock predictor
        bedrock_client = boto3.client("bedrock-runtime", region_name=bedrock_config["region"])
        embeddings = BedrockEmbeddings(
            client=bedrock_client,
            model_id=bedrock_config["model_id"])
        embedding_provider = "bedrock"
    else:
        raise Exception("Bedrock or Huggingface config is required")

    docsearch = OpenSearchVectorSearch(
        index_name=os_index_name,
        embedding_function=embeddings,
        opensearch_url=os_domain_ep,
        
        http_auth=os_http_auth,
        timeout = 300,
        connection_class = RequestsHttpConnection,
        use_ssl=True,
        verify_certs=True,
    )
    print(f"embedding {len(docs)} documents using {embedding_provider}")

    # Calculate the total number of batches
    batch_size = 10
    num_batches = (len(docs) + batch_size - 1) // batch_size

    # Assuming docs is your list of documents
    for batch in tqdm(chunked_iterable(docs, batch_size), total=num_batches):
        docsearch.add_documents(documents=batch)

