import json
import re
from typing import List, Dict, Any  # added

# Test input/output files
INPUT_FILE = "bank_knowledge_test.json"
OUTPUT_FILE = "bank_documents_test.json"


def is_question(text: str) -> bool:
    """
    Decide whether a line is a real question.
    """
    text = text.strip()

    if not text:
        return False

    # most real questions end with ?
    if text.endswith("?"):
        return True

    # also allow common bank FAQ patterns
    question_starters = [
        "what", "how", "when", "where", "which",
        "who", "can", "is", "are", "does", "do",
    ]

    first_word = text.lower().split()[0]
    return first_word in question_starters


def normalize_profit_table(answer: str) -> str:
    """
    Detects profit payment / profit rate fragments in two common patterns:
    1) Table-ish: 'Monthly 0.19', 'Quarterly 0.1905', 'Semi-Annually 0.191', 'Annually 0.1915'
    2) Single: 'Profit Payment Profit Rate ... Semi-Annually 0.19'

    Removes these numeric fragments from the main answer text and appends
    a clean 'Profit Payment / Profit Rate' block at the end.
    """
    # Normalize spaces
    text = " ".join(answer.split())

    # ----- Pattern 1: Table-ish rows -----
    pattern_table = re.compile(
        r"(Monthly|Quarterly|Semi-Annually|Annually)\s+([0-9]+(?:\.[0-9]+)?%?)",
        re.IGNORECASE,
    )

    rows = []
    used_spans = []

    for m in pattern_table.finditer(text):
        period = m.group(1)
        rate = m.group(2)
        rows.append((period, rate))
        used_spans.append((m.start(), m.end()))

    # ----- Pattern 2: single Profit Payment / Rate -----
    # e.g. "... Profit Payment Profit Rate ... Semi-Annually 0.19 ..."
    if not rows:
        pattern_single = re.compile(
            r"Profit\s+Payment\s+Profit\s+Rate.*?(Monthly|Quarterly|Semi-Annually|Annually)\s+([0-9]+(?:\.[0-9]+)?%?)",
            re.IGNORECASE,
        )
        m = pattern_single.search(text)
        if m:
            period = m.group(1)
            rate = m.group(2)
            rows.append((period, rate))
            used_spans.append((m.start(1), m.end(2)))  # remove only freq+rate

    # If still nothing found, return original answer
    if not rows:
        return answer

    # Remove matched fragments from text
    cleaned_parts = []
    last_end = 0
    for start, end in sorted(used_spans):
        cleaned_parts.append(text[last_end:start])
        last_end = end
    cleaned_parts.append(text[last_end:])
    cleaned_text = " ".join("".join(cleaned_parts).split())

    # Build profit table block
    table_lines = ["Profit Payment / Profit Rate:"]
    for period, rate in rows:
        table_lines.append(f"{period}: {rate}")

    table_block = "\n".join(table_lines)

    if cleaned_text:
        return cleaned_text.strip() + "\n\n" + table_block
    else:
        return table_block


def create_documents_test() -> List[Dict[str, Any]]:
    """
    Read bank_knowledge_test.json and produce docs in RAG format.
    Returns the list of docs, and also writes bank_documents_test.json to disk.
    """
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents: List[Dict[str, Any]] = []
    current_doc: Dict[str, Any] | None = None

    for item in data:
        sheet = item.get("sheet", "Unknown")
        question_text = item.get("question", "").strip()
        answer_text = item.get("answer", "").strip()

        # SPECIAL CASE: rate sheet → one document per JSON row
        if sheet == "Rate Sheet July 1 2024":
            combined_answer = (question_text + " " + answer_text).strip()
            documents.append(
                {
                    "sheet": sheet,
                    "question": f"Rate sheet row: {question_text[:60]}",
                    "answer": combined_answer,
                }
            )
            continue

        # Generic behavior for all other sheets (same as before)
        if is_question(question_text):
            # save previous document
            if current_doc:
                documents.append(current_doc)

            # start new document
            current_doc = {
                "sheet": sheet,
                "question": question_text,
                "answer": answer_text,
            }
        else:
            # not a question → append to previous answer
            if current_doc:
                addition = question_text
                if answer_text:
                    addition += " " + answer_text
                current_doc["answer"] += "\n" + addition

    # add last document
    if current_doc:
        documents.append(current_doc)

    # convert to RAG format
    final_docs: List[Dict[str, Any]] = []

    for doc in documents:
        normalized_answer = normalize_profit_table(doc["answer"])

        text = f"""
Product Area: {doc['sheet']}

Question: {doc['question']}

Answer:
{normalized_answer}
""".strip()

        final_docs.append(
            {
                "content": text,
                "metadata": {
                    "sheet": doc["sheet"],
                    "question": doc["question"],
                },
            }
        )

    print("Original rows (test):", len(data))
    print("Final documents (test):", len(final_docs))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_docs, f, indent=2, ensure_ascii=False)

    print(f"[test_prepare_documents] Wrote {len(final_docs)} docs to {OUTPUT_FILE}.")

    return final_docs


if __name__ == "__main__":
    create_documents_test()
