# build_index.py

import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


INPUT_FILE = "bank_documents.json"
INDEX_DIR = "vector_store"
INDEX_FILE = "faiss_index.bin"
METADATA_FILE = "metadata.json"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def build_index():
    os.makedirs(INDEX_DIR, exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        documents = json.load(f)

    texts = [doc["content"] for doc in documents]

    # Attach full content into metadata so retrieve.py can return it
    metadata = []
    for doc in documents:
        m = doc["metadata"].copy()
        m["content"] = doc["content"]
        metadata.append(m)

    print("Total documents:", len(texts))

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print("Creating embeddings...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    print("Total vectors in index:", index.ntotal)

    faiss.write_index(index, os.path.join(INDEX_DIR, INDEX_FILE))

    with open(os.path.join(INDEX_DIR, METADATA_FILE), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("Index and metadata saved successfully!")


def load_index(index_dir: str = INDEX_DIR):
    index = faiss.read_index(os.path.join(index_dir, INDEX_FILE))
    with open(os.path.join(index_dir, METADATA_FILE), "r", encoding="utf-8") as f:
        metadata = json.load(f)
    return index, metadata


if __name__ == "__main__":
    build_index()
