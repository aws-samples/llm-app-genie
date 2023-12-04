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