import torch
from transformers import AutoModel, AutoTokenizer


def average_pool(
    last_hidden_states: torch.Tensor, attention_mask: torch.Tensor
) -> torch.Tensor:
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


def model_fn(model_dir):
    # Load model from HuggingFace Hub
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModel.from_pretrained(model_dir)
    return model, tokenizer


def predict_fn(data, model_and_tokenizer):
    # destruct model and tokenizer
    model, tokenizer = model_and_tokenizer
    print(data)
    # Tokenize documents
    texts = data.pop("texts", data)
    isQuery = data.pop("isQuery", False)
    prefix = "passage: "
    if isQuery:
        prefix = "query: "

    texts = [prefix + t for t in texts]
    # Tokenize the input texts
    encoded_input = tokenizer(
        texts, max_length=512, padding=True, truncation=True, return_tensors="pt"
    )

    # Compute token embeddings
    with torch.no_grad():
        model_output = model(**encoded_input)

    # Perform pooling
    embeddings = average_pool(
        model_output.last_hidden_state, encoded_input["attention_mask"]
    )

    # return dictonary, which will be json serializable
    return {"vectors": embeddings.detach().numpy().tolist()}
