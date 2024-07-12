from bs4 import BeautifulSoup
import re
from langchain.schema import Document

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

def generate_embeddings(df):
    docs = []
    for _, row in df.iterrows():
        for _, paragraph in enumerate(row["paragraphs"]):
            meta = {"source": row["source"], "title": row["title"]}
            doc = Document(page_content=paragraph, metadata=meta)
            docs.append(doc)
    return docs