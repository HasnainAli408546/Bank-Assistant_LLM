# build_index_test.py

import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = os.path.dirname(__file__)
DOC_PATH = os.path.join(PROJECT_ROOT, "bank_documents_test.json")
INDEX_DIR = os.path.join(PROJECT_ROOT, "vector_store_test")
INDEX_FILE = "faiss_index_test.bin"
METADATA_FILE = "metadata_test.json"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def build_faiss_test():
    os.makedirs(INDEX_DIR, exist_ok=True)

    with open(DOC_PATH, "r", encoding="utf-8") as f:
        docs = json.load(f)

    num_docs = len(docs)
    print(f"[build_index_test] Loaded {num_docs} documents from {DOC_PATH}")

    texts = [d["content"] for d in docs]

    print(f"[build_index_test] Loading embedding model: {EMBEDDING_MODEL_NAME}")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print(f"[build_index_test] Computing embeddings for {num_docs} documents...")
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    d = embeddings.shape[1]
    print(f"[build_index_test] Embedding dimension: {d}")

    index = faiss.IndexFlatL2(d)
    index.add(embeddings)

    print(f"[build_index_test] FAISS index now contains {index.ntotal} vectors")

    faiss.write_index(index, os.path.join(INDEX_DIR, INDEX_FILE))
    print(f"[build_index_test] FAISS index written to {os.path.join(INDEX_DIR, INDEX_FILE)}")

    metadata = []
    for doc in docs:
        m = doc["metadata"].copy()
        m["content"] = doc["content"]
        metadata.append(m)

    meta_path = os.path.join(INDEX_DIR, METADATA_FILE)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"[build_index_test] Metadata for {len(metadata)} docs written to {meta_path}")
    print(f"[build_index_test] Built FAISS TEST index with {index.ntotal} vectors.")


if __name__ == "__main__":
    build_faiss_test()
