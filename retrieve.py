# retrieve.py

import json
from typing import List, Dict

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from build_index import load_index, EMBEDDING_MODEL_NAME


def load_documents(path: str = "bank_documents.json") -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def search(
    query: str,
    k: int = 5,
    index_dir: str = "vector_store",
) -> List[Dict]:
    """
    Return top-k chunks with metadata and scores.
    """
    index, metadata = load_index(index_dir)
    model = load_embedding_model()

    q_emb = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    scores, idxs = index.search(q_emb, k)  # scores = cosine similarity

    results: List[Dict] = []
    for score, idx in zip(scores[0], idxs[0]):
        meta = metadata[idx].copy()
        # meta should already contain "chunk_text", "sheet", "question", ...
        meta["score"] = float(score)
        results.append(meta)

    return results


if __name__ == "__main__":
    # Simple manual test from terminal
    while True:
        q = input("\nEnter query (or 'exit'): ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        hits = search(q, k=5)
        for h in hits:
            print("\n---")
            print("Score:", round(h["score"], 3))
            print("Sheet:", h.get("sheet"))
            print("Question:", h.get("question"))
            print("Chunk:", h.get("chunk_text", "")[:400], "...")
