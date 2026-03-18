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
    # Ensure output dir exists
    os.makedirs(INDEX_DIR, exist_ok=True)

    # Load documents
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        documents = json.load(f)

    texts = [doc["content"] for doc in documents]
    metadata = [doc["metadata"] for doc in documents]

    print("Total documents:", len(texts))

    # Load embedding model (CPU-friendly)
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print("Creating embeddings...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # keep in sync with retrieve.py
    ).astype("float32")

    dim = embeddings.shape[1]

    # Use L2 index over normalized vectors (works fine for semantic search)
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    print("Total vectors in index:", index.ntotal)

    # Save index
    faiss.write_index(index, os.path.join(INDEX_DIR, INDEX_FILE))

    # Save metadata
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
