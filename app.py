from typing import List, Dict, Any, Optional

import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
import shutil
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from openai import OpenAI

from retrieve import (
    init_faiss_index,
    search,
    build_rag_document,
    upsert_docs,
)

from extract_knowledge import extract_knowledge_from_excel
from prepare_documents import create_documents  # main (non-test) version


# ---- Env + OpenRouter config ----

load_dotenv()  # load .env

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("Set OPENROUTER_API_KEY in your environment.")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# You can switch between 1B / 3B etc. here
MODEL_ID = "meta-llama/llama-3.2-3b-instruct"

# Short answers + lighter context
MAX_TOKENS = 128
TOP_K = 3  # default max docs per query

# Upload dir for Excel
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---- Load FAISS MAIN index at startup ----

init_faiss_index()  # loads faiss_index.bin + metadata.json into memory


# ---- LLM helper (OpenRouter) ----

def generate_llama_answer(prompt: str, max_tokens: int = MAX_TOKENS) -> str:
    """Call Llama 3.2 via OpenRouter with strict grounding."""
    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "http://localhost:8000",
            "X-OpenRouter-Title": "NUST Bank Assistant",
        },
        model=MODEL_ID,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a bank FAQ assistant for NUST Bank (fictional).\n"
                    "You must base your answers on the provided bank documents. You may paraphrase or combine information, "
                    "and you may infer obvious implications from what is written, but do not invent new products, numbers, or details that are not supported by the documents.\n"
                    "For example, if an account is opened in the name of a minor, you may describe it as an account for minors or children.\n"
                    "If the answer is not clearly stated in the documents and you cannot reasonably infer it, reply exactly: "
                    "\"I do not know based on the available documents.\"\n"
                    "Never invent or guess numbers, amounts, rates, balances, limits, account names, or product names.\n"
                    "When you mention an account or product, use its exact name from the documents "
                    "(for example, \"Little Champs Account\").\n"
                    "Use a polite, concise tone and answer in 1–3 short sentences.\n"
                    "Do not expose your internal reasoning, steps, or which sentence you selected."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        max_tokens=max_tokens,
        temperature=0.3,  # slightly lower for factual QA
        top_p=0.9,
    )
    return completion.choices[0].message.content.strip()


# ---- FastAPI app & models ----

app = FastAPI(title="NUST Bank Assistant API (MAIN index · OpenRouter Llama 3.2)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # OK for local dev; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str = Field(..., description="Current user question (no history)")
    top_k: int = Field(TOP_K, description="Number of documents to retrieve")
    history: Optional[str] = Field(
        None,
        description="Recent conversation history for pronoun resolution",
    )


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]


class AddDocRequest(BaseModel):
    sheet: str
    question: str
    answer: str


class AddDocResponse(BaseModel):
    status: str
    count: int


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


def build_context(hits: List[Dict[str, Any]]) -> str:
    parts = []
    for i, h in enumerate(hits, start=1):
        # MAIN metadata has full content in "content"
        ctx = h.get("content", "")
        ctx = ctx[:800]  # light truncation
        sheet = h.get("sheet", "Unknown")
        question = h.get("question", "")
        parts.append(
            f"[Source {i} | Product Area: {sheet} | Question: {question}]\n{ctx}"
        )
    return "\n\n".join(parts)


def build_user_prompt(
    user_query: str,
    hits: List[Dict[str, Any]],
    history: Optional[str] = None,
) -> str:
    context = build_context(hits)

    history_block = ""
    if history:
        history_block = (
            "Conversation so far:\n"
            f"{history}\n\n"
            "Use this conversation history ONLY to resolve references like 'it', 'that account', or 'this account'. "
            "Otherwise, focus on the current user question.\n\n"
        )

    user_part = (
        "You are answering questions based on the bank documents below.\n"
        f"{history_block}"
        "Bank documents:\n"
        f"{context}\n\n"
        f"User question: {user_query}\n\n"
        "Instructions:\n"
        "- Use the bank documents above to answer the current user question as directly as possible.\n"
        "- Always focus on the current user question. Use the conversation history only when the question "
        "uses pronouns like 'it', 'that account', or 'this account' that need resolution.\n"
        "- It is allowed to restate or slightly generalize what the documents say "
        "(for example, if an account is opened in the name of a minor, you may describe it as an account for minors or children).\n"
        "- Then respond to the user in 1–3 short, clear sentences.\n"
        "- Copy all numeric amounts, rates, and limits exactly from the documents.\n"
        "- If you truly cannot find any relevant information in the documents, reply exactly: "
        "\"I do not know based on the available documents.\"\n"
        "- When the documents describe one or more specific accounts or products that fit the question, "
        "explicitly name the most relevant ones using the exact names from the documents "
        "(for example, \"Little Champs Account\"), and mention one or two key features.\n"
        "- If the question asks about different accounts, types of accounts, or a list of accounts/products, "
        "and the documents list multiple products, then list several relevant accounts instead of focusing on a single one.\n"
        "- If the question is asking which account or product is suitable for a goal "
        "(for example, starting a business, saving for children, women-specific banking, or senior citizens), "
        "choose the account(s) whose description best matches that goal and briefly explain why they are suitable.\n"
        "- When recommending accounts, respect any eligibility constraints mentioned in the documents "
        "(for example, minimum age, women-only, minors-only) and avoid recommending accounts the user clearly does not qualify for.\n"
        "- Do not repeat answers about a previous account if the current question introduces a new goal "
        "or asks about a different type of account.\n"
        "- Important: Do your reasoning internally and only output the final answer to the user. "
        "Do NOT mention steps, internal reasoning, or which sentence you selected.\n"
    )

    return user_part


# ---- Endpoints ----

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # req.query is ONLY the current user question
    if is_disallowed_input(req.query):
        return ChatResponse(
            answer=(
                "For your security, I cannot help with PINs, passwords, or similar "
                "sensitive information. Please contact the bank through official "
                "channels for such requests."
            ),
            sources=[],
        )

    top_k = min(req.top_k, TOP_K)

    # Retrieval based only on current question (MAIN index)
    hits = search(req.query, k=top_k)

    print("\n[DEBUG] Retrieved hits for:", req.query)
    for i, h in enumerate(hits, 1):
        print(f"--- Hit {i} ---")
        print("Score (L2, lower=better):", h.get("score"))
        print("Sheet:", h.get("sheet"))
        print("Question:", h.get("question"))
        print("Content snippet:", h.get("content", "")[:400], "...\n")

    if not hits:
        return ChatResponse(
            answer="I do not know based on the available documents.",
            sources=[],
        )

    user_prompt = build_user_prompt(req.query, hits, history=req.history)
    print("\n[DEBUG] Prompt sent to LLM (user content):\n", user_prompt[:2000], "\n")

    answer = generate_llama_answer(user_prompt, max_tokens=MAX_TOKENS)
    print("\n[DEBUG] Raw LLM answer:\n", answer, "\n")

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


@app.post("/add_document", response_model=AddDocResponse)
def add_document_endpoint(req: AddDocRequest):
    # Build one RAG doc from the input
    new_doc = build_rag_document(
        sheet=req.sheet,
        question=req.question,
        answer=req.answer,
    )

    # Upsert it (remove old (sheet, question) if exists, then add)
    upsert_docs([new_doc])

    return AddDocResponse(status="ok", count=1)


@app.post("/upload_excel", response_model=AddDocResponse)
async def upload_excel(file: UploadFile = File(...)):
    """
    Upload an Excel file and upsert docs:
    Excel -> bank_knowledge.json -> docs -> upsert into bank_documents.json -> rebuild FAISS.
    """
    # 1) Save uploaded file
    tmp_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(tmp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2) Excel -> bank_knowledge.json
    extract_knowledge_from_excel(tmp_path)

    # 3) bank_knowledge.json -> docs (list in memory)
    docs_from_excel = create_documents()  # main version returns List[Dict]

    # 4) Upsert these docs into bank_documents.json and rebuild FAISS
    upsert_docs(docs_from_excel)

    return AddDocResponse(status="ok", count=len(docs_from_excel))