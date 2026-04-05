# retrieve.py

import json
import os
from typing import List, Dict, Any, Optional

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

import pandas as pd  # for CSV / Excel ingestion if you want later


# ------------ Config ------------

PROJECT_ROOT = os.path.dirname(__file__)

# Main (non-test) paths
BANK_DOCS_PATH = os.path.join(PROJECT_ROOT, "bank_documents.json")
INDEX_DIR = os.path.join(PROJECT_ROOT, "vector_store")
INDEX_FILE = "faiss_index.bin"
METADATA_FILE = "metadata.json"

os.makedirs(INDEX_DIR, exist_ok=True)

# Must match build_index.py
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Global in-memory FAISS objects (MAIN index)
_model: Optional[SentenceTransformer] = None
_faiss_index: Optional[faiss.Index] = None
_metadata: List[Dict[str, Any]] = []


# ------------ Core utilities ------------

def _ensure_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def _load_faiss_and_metadata():
    """
    Load MAIN FAISS index and metadata.json from disk.
    Called once in init_faiss_index().
    """
    global _faiss_index, _metadata

    index_path = os.path.join(INDEX_DIR, INDEX_FILE)
    meta_path = os.path.join(INDEX_DIR, METADATA_FILE)

    if not os.path.exists(index_path):
        raise FileNotFoundError(f"FAISS index not found at {index_path}")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Metadata file not found at {meta_path}")

    _faiss_index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        _metadata = json.load(f)


def _save_metadata():
    """
    Persist updated metadata list back to vector_store/metadata.json.
    """
    meta_path = os.path.join(INDEX_DIR, METADATA_FILE)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(_metadata, f, ensure_ascii=False, indent=2)


def _append_to_bank_documents(doc: Dict[str, Any]):
    """
    Append a new RAG document to bank_documents.json on disk.
    """
    docs: List[Dict[str, Any]] = []
    if os.path.exists(BANK_DOCS_PATH):
        with open(BANK_DOCS_PATH, "r", encoding="utf-8") as f:
            docs = json.load(f)

    docs.append(doc)

    with open(BANK_DOCS_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


# ------------ Initialization (MAIN index) ------------

def init_faiss_index():
    """
    Call this once at app startup (for MAIN index).
    Loads FAISS index + metadata into memory and the embedding model.
    """
    _ensure_model()
    _load_faiss_and_metadata()
    print(
        f"[retrieve] Loaded FAISS index with "
        f"{_faiss_index.ntotal} vectors and {len(_metadata)} metadata entries."
    )


# ------------ Search (MAIN index) ------------

def search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Semantic search over MAIN FAISS index.
    Returns top-k documents with metadata and L2 distances (lower is better).
    """
    global _faiss_index, _metadata

    if _faiss_index is None or not _metadata:
        return []

    _ensure_model()

    q_emb = _model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    distances, idxs = _faiss_index.search(q_emb, k)

    results: List[Dict[str, Any]] = []
    for dist, idx in zip(distances[0], idxs[0]):
        meta = _metadata[idx].copy()
        meta["score"] = float(dist)  # lower is better
        results.append(meta)

    return results


# ------------ Incremental FAISS updates (MAIN index) ------------

def add_document_faiss(doc: Dict[str, Any]):
    """
    Add a single new document to the MAIN index:
    - bank_documents.json (on disk)
    - FAISS index in memory
    - metadata list + metadata.json on disk

    Expected doc format (same as bank_documents.json):
    {
        "content": "Product Area: ...\\n\\nQuestion: ...\\n\\nAnswer:\\n...",
        "metadata": {
            "sheet": "NAA",
            "question": "What is ...?"
        }
    }
    """
    global _faiss_index, _metadata

    if _faiss_index is None:
        raise RuntimeError("FAISS index not initialized. Call init_faiss_index() first.")

    _ensure_model()

    content = doc.get("content", "")
    meta = doc.get("metadata", {})

    # 1) Compute embedding for this new content
    emb = _model.encode(
        [content],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    # 2) Add to FAISS index in memory
    _faiss_index.add(emb)

    # 3) Append metadata (including content) in memory and persist
    meta_full = meta.copy()
    meta_full["content"] = content
    _metadata.append(meta_full)
    _save_metadata()

    # 4) Append the doc itself to bank_documents.json on disk
    _append_to_bank_documents(doc)

    print(
        f"[retrieve] Added new document to FAISS index. "
        f"New total: {_faiss_index.ntotal}"
    )


# ------------ Helpers to build doc from simple text ------------

def build_rag_document(sheet: str, question: str, answer: str) -> Dict[str, Any]:
    """
    Build a RAG-style document (content + metadata) similar to prepare_documents.py.
    Does NOT do profit-table normalization; you can extend if needed.
    """
    content = f"""
Product Area: {sheet}


Question: {question}


Answer:
{answer}
""".strip()

    return {
        "content": content,
        "metadata": {
            "sheet": sheet,
            "question": question,
        },
    }


def ingest_excel_to_faiss(path: str):
    """
    Read an Excel file (all sheets) and ingest rows as RAG documents
    into the MAIN FAISS index + bank_documents.json + metadata.json.

    Expected columns in each sheet:
        - sheet       (or will fallback to sheet name)
        - question
        - answer
    """
    if pd is None:
        raise ImportError("pandas is required for ingest_excel_to_faiss")

    if _faiss_index is None:
        raise RuntimeError("FAISS index not initialized. Call init_faiss_index() first.")

    # sheet_name=None -> dict: {sheet_name: DataFrame}
    sheets_dict = pd.read_excel(path, sheet_name=None)

    for sheet_name, df in sheets_dict.items():
        # Try to detect columns; you can enforce names if you prefer
        cols = {c.lower(): c for c in df.columns}

        q_col = cols.get("question")
        a_col = cols.get("answer")
        s_col = cols.get("sheet")  # optional; will fallback to sheet_name

        if q_col is None or a_col is None:
            # Skip sheets that don't look like QA sheets
            print(
                f"[ingest_excel_to_faiss] Skipping sheet '{sheet_name}' "
                f"(missing question/answer columns)."
            )
            continue

        for _, row in df.iterrows():
            sheet_val = str(row.get(s_col, sheet_name)) if s_col else str(sheet_name)
            question = str(row.get(q_col, "")).strip()
            answer = str(row.get(a_col, "")).strip()

            if not question or not answer:
                continue

            doc = build_rag_document(sheet=sheet_val, question=question, answer=answer)
            add_document_faiss(doc)

    print("[ingest_excel_to_faiss] Finished ingesting Excel file:", path)


def upsert_docs(new_docs: List[Dict[str, Any]]) -> int:
    """
    Upsert a list of docs into bank_documents.json using (sheet, question) as key.
    For each incoming doc, if same (sheet, question) exists, replace it; otherwise append.
    Then rebuild FAISS index and reload it.
    """
    # 1) Load existing docs
    docs: List[Dict[str, Any]] = []
    if os.path.exists(BANK_DOCS_PATH):
        with open(BANK_DOCS_PATH, "r", encoding="utf-8") as f:
            docs = json.load(f)

    # 2) Put existing docs into a dict keyed by (sheet, question)
    index_map: Dict[tuple, Dict[str, Any]] = {}
    for d in docs:
        meta = d.get("metadata", {})
        key = (meta.get("sheet"), meta.get("question"))
        index_map[key] = d

    # 3) Upsert new docs
    for nd in new_docs:
        meta = nd.get("metadata", {})
        key = (meta.get("sheet"), meta.get("question"))
        index_map[key] = nd  # replace if exists, else insert

    # 4) Convert back to list and save
    updated_docs = list(index_map.values())
    with open(BANK_DOCS_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_docs, f, ensure_ascii=False, indent=2)

    # 5) Rebuild FAISS index + reload
    from build_index import build_index
    build_index()        # rebuild from updated JSON
    init_faiss_index()   # reload in memory

    return len(new_docs)


# ------------ CLI test (MAIN index) ------------

if __name__ == "__main__":
    print("Initializing FAISS index...")
    init_faiss_index()
    print(f"Metadata entries: {len(_metadata)}")

    while True:
        q = input("\nEnter query (or 'exit'): ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        hits = search(q, k=5)
        for h in hits:
            print("\n---")
            print("Distance (lower=better):", round(h["score"], 3))
            print("Sheet:", h.get("sheet"))
            print("Question:", h.get("question"))
            print("Content:", h.get("content", "")[:400], "...")