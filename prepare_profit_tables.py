# prepare_profit_tables.py

import json
import re
from typing import Dict, Any, List

INPUT_FILE = "bank_knowledge.json"
OUTPUT_FILE = "profit_tables.json"


def extract_profit_rows(answer: str) -> Dict[str, str]:
    """
    Extracts profit payment / profit rate info into a dict like:
    {
        "Monthly": "19.00%",
        "Quarterly": "19.05%",
        "Semi-Annually": "19.10%",
        "Annually": "19.15%"
    }
    or for single entries:
    {
        "Semi-Annually": "19.00%"
    }
    """
    text = " ".join(answer.split())

    pattern = re.compile(
        r"(Monthly|Quarterly|Semi-Annually|Annually)\s+([0-9]+(?:\.[0-9]+)?%?)",
        re.IGNORECASE,
    )

    rows: Dict[str, str] = {}
    for m in pattern.finditer(text):
        period = m.group(1)
        rate = m.group(2)
        rows[period] = rate

    # Fallback: look for single 'Profit Payment Profit Rate ...'
    if not rows:
        pattern_single = re.compile(
            r"Profit\s+Payment\s+Profit\s+Rate.*?(Monthly|Quarterly|Semi-Annually|Annually)\s+([0-9]+(?:\.[0-9]+)?%?)",
            re.IGNORECASE,
        )
        m = pattern_single.search(text)
        if m:
            period = m.group(1)
            rate = m.group(2)
            rows[period] = rate

    return rows


def create_profit_tables() -> None:
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    tables: List[Dict[str, Any]] = []

    for item in data:
        sheet = item.get("sheet", "Unknown")
        question = item.get("question", "").strip()
        answer = item.get("answer", "").strip()

        # Only look at rows that are clearly about profit / rate
        if "profit" not in question.lower() and "profit" not in answer.lower():
            continue

        rows = extract_profit_rows(answer)
        if not rows:
            continue

        tables.append(
            {
                "sheet": sheet,
                "question": question,
                "profit_payment": rows,
            }
        )

    print("Extracted profit tables for", len(tables), "rows")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(tables, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    create_profit_tables()
