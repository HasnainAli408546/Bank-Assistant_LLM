import json
import re

INPUT_FILE = "bank_knowledge.json"
OUTPUT_FILE = "bank_documents.json"


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
    Detect fragments like 'Monthly 0.19', 'Quarterly 0.1905', 'Semi-Annually 0.191', 'Annually 0.1915'
    scattered inside the answer, remove them from their original positions, and append a
    clean table block at the end.

    Returns a new answer string.
    """
    # Normalize spaces
    text = " ".join(answer.split())

    # Regex: (Monthly|Quarterly|Semi-Annually|Annually) + number (e.g., 0.19, 19.00, 19.05%)
    pattern = re.compile(
        r"(Monthly|Quarterly|Semi-Annually|Annually)\s+([0-9]+(?:\.[0-9]+)?%?)",
        re.IGNORECASE,
    )

    rows = []
    used_spans = []

    for m in pattern.finditer(text):
        period = m.group(1)
        rate = m.group(2)
        rows.append((period, rate))
        used_spans.append((m.start(), m.end()))

    # If fewer than 2 rows, do nothing (likely not a real table)
    if len(rows) < 2:
        return answer

    # Remove matched fragments from text
    cleaned_parts = []
    last_end = 0
    for start, end in used_spans:
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


def create_documents() -> None:
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    current_doc = None

    for item in data:
        sheet = item.get("sheet", "Unknown")
        question_text = item.get("question", "").strip()
        answer_text = item.get("answer", "").strip()

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
    final_docs = []

    for doc in documents:
        # Normalize answer to pull out profit-rate table fragments
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

    print("Original rows:", len(data))
    print("Final documents:", len(final_docs))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_docs, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    create_documents()
