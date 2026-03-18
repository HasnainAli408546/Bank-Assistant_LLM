# app.py

from typing import List, Dict, Any
import requests

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from retrieve import search  # semantic search over bank_documents.json


# ---- Config ----

LLM_API_URL = "http://localhost:9000/generate"
MAX_TOKENS = 96          # a bit more room than 64
TOP_K = 3                # fewer docs → more focused context


# ---- LLM client ----

def call_llm(prompt: str, max_tokens: int = MAX_TOKENS) -> str:
    try:
        resp = requests.post(
            LLM_API_URL,
            json={"prompt": prompt, "max_tokens": max_tokens},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("text", "").strip()
    except Exception as e:
        print("LLM call failed:", e)
        return (
            "I'm sorry, but I'm currently unable to answer your question due to a system error."
        )


# ---- FastAPI app & models ----

app = FastAPI(title="NUST Bank Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # OK for local dev; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str = Field(..., description="User question")
    top_k: int = Field(TOP_K, description="Number of documents to retrieve")


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]


# ---- Guardrails + prompt helpers ----

def is_disallowed_input(text: str) -> bool:
    text_l = text.lower()
    sensitive_keywords = [
        "pin",
        "password",
        "otp",
        "cvv",
        "cvc",
        "bypass security",
        "hack",
        "jailbreak",
    ]
    return any(k in text_l for k in sensitive_keywords)


def build_system_prompt() -> str:
    return (
        "You are a bank FAQ assistant for NUST Bank (fictional).\n"
        "You MUST answer ONLY using the information in the provided documents.\n"
        "If the answer is not clearly stated there, reply exactly: \"I do not know based on the available documents.\"\n"
        "Do NOT guess or invent numbers (amounts, rates, balances, limits).\n"
        "When the question is about opening or minimum balance, or profit rate, copy the numbers "
        "and conditions exactly from the documents.\n\n"
    )


def build_context(hits: List[Dict[str, Any]]) -> str:
    parts = []
    for i, h in enumerate(hits, start=1):
        ctx = h.get("content", "")  # <-- matches prepare_documents.py
        sheet = h.get("sheet", "Unknown")
        question = h.get("question", "")
        parts.append(
            f"[Source {i} | Product Area: {sheet} | Question: {question}]\n{ctx}"
        )
    return "\n\n".join(parts)


def build_prompt(user_query: str, hits: List[Dict[str, Any]]) -> str:
    system = build_system_prompt()
    context = build_context(hits)

    user_part = (
        "Bank documents:\n"
        f"{context}\n\n"
        f"User question: {user_query}\n\n"
        "Step 1: From the documents above, identify the exact sentence or phrase that answers the question.\n"
        "Step 2: Answer in 1–3 short sentences, copying all numeric amounts and limits exactly from the documents.\n"
        "If you cannot find a clear answer, reply exactly: \"I do not know based on the available documents.\"\n"
    )

    return system + user_part


# ---- Endpoints ----

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # Basic guardrail
    if is_disallowed_input(req.query):
        return ChatResponse(
            answer=(
                "For your security, I cannot help with PINs, passwords, or similar sensitive information. "
                "Please contact the bank through official channels for such requests."
            ),
            sources=[],
        )

    # Retrieve top-k docs (can be overridden by client)
    hits = search(req.query, k=req.top_k)

    # If nothing retrieved, fail gracefully
    if not hits:
        return ChatResponse(
            answer="I do not know based on the available documents.",
            sources=[],
        )

    # Build extraction-focused prompt
    prompt = build_prompt(req.query, hits)
    answer = call_llm(prompt)

    return ChatResponse(
        answer=answer,
        sources=[
            {
                "sheet": h.get("sheet"),
                "question": h.get("question"),
                "score": h.get("score"),
            }
            for h in hits
        ],
    )
