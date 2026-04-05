import pandas as pd
import json
import re

output_file = "bank_knowledge_test.json"


def is_question(text: str) -> bool:
    """
    Detect whether a text line is a question.
    """
    text = text.lower().strip()

    question_words = (
        "what", "how", "who", "where", "why", "when",
        "can", "is", "are", "does", "do", "will",
        "which"
    )

    faq_keywords = (
        "features",
        "benefits",
        "charges",
        "documents",
        "requirements",
        "target market",
        "eligibility",
        "profit rate",
        "profit payment",
    )

    if text.endswith("?"):
        return True

    if text.startswith(question_words):
        return True

    for k in faq_keywords:
        if k in text:
            return True

    return False


def extract_products_from_main_sheet(sheet_name: str, df: pd.DataFrame):
    """
    From 'Main', build a single catalog QA:
    - Question: list of accounts / products
    - Answer: comma-separated product names (with codes) from the sheet.
    """
    # Keywords that usually appear in product names
    PRODUCT_KEYWORDS = [
        "account",
        "finance",
        "remittance",
        "deposit",
        "card",
        "policy",
        "loan",
        "scheme",
    ]

    products = set()
    row_count = 0

    for _, row in df.iterrows():
        cells = [str(cell).strip() for cell in row if pd.notna(cell)]
        if not cells:
            continue

        text = " ".join(cells)
        row_count += 1

        lower = text.lower()
        # Skip obvious headers
        if "nust bank products" in lower or "click on any product" in lower:
            continue
        if "liability products" in lower or "consumer products" in lower:
            continue
        if "sme products" in lower or "third party products" in lower:
            continue

        tokens = text.split()
        while tokens and tokens[0].isdigit():
            tokens.pop(0)
        cleaned_text = " ".join(tokens)

        parts = re.split(r"\s\d+\s", cleaned_text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            lower_part = part.lower()

            if any(k in lower_part for k in PRODUCT_KEYWORDS):
                products.add(part)

    products = sorted(products)
    print(f"[Main] rows scanned: {row_count}, unique products found: {len(products)}")

    if not products:
        return []

    # Single catalog QA
    question = "What are the main accounts and products offered by NUST Bank?"
    # You can tweak wording; include codes inline if present in text (e.g. "(NAA)")
    answer = "NUST Bank offers the following products: " + "; ".join(products) + "."

    return [
        {
            "sheet": sheet_name,
            "question": question,
            "answer": answer,
            "meta": {
                "type": "product_catalog",
                "products": products,
            },
        }
    ]


# ----------------- NEW: Rate Sheet helpers ----------------- #

def extract_savings_accounts_from_rate_sheet(sheet_name: str, df: pd.DataFrame):
    """
    Left side of the Rate Sheet:
    savings accounts with 2-column tables:
    Profit Payment | Profit Rate.
    Also emits product-centric duplicate QAs (e.g. NAA, LCA) for better retrieval.
    """
    COL_LABEL = 1    # text: account names, 'Profit Payment', 'Semi-Annually', etc.
    COL_RATE = 3     # numeric: profit rate

    # Map of full name -> short code you want to support in queries
    SAVINGS_SHORT_CODES = {
        "NUST Asaan Account": "NAA",
        "Little Champs Account": "LCA",
        "NUST Special Deposit Account (ASDA)": "ASDA",
        "NUST Waqaar Account - Senior Citizen": "WAA",
        "PakWatan Remittance Account": "PWRA",
        "NUST Sahar Savings Account": "Sahar Savings",
        "NUST Maximiser Savings Account": "Maximiser Savings",
        "PLS Savings": "PLSS",
        "PLS Pensioners Account": "PLSPA",
    }

    current_account = None
    rows = []

    print(f"\n[RateSheet] Scanning rows for savings accounts (left) in '{sheet_name}'...\n")

    for idx, row in df.iterrows():
        label = str(row[COL_LABEL]).strip() if COL_LABEL in row else ""
        rate = str(row[COL_RATE]).strip() if COL_RATE in row else ""

        if label.lower().startswith("nan"):
            label = ""
        if rate.lower().startswith("nan"):
            rate = ""

        lower_label = label.lower()

        # 1) Detect savings account header
        if label and not rate and any(
            kw in lower_label
            for kw in [
                "account",       # catches 'NUST Asaan Account', 'Little Champs Account', etc.
                "saving", "savings"
            ]
        ) and not any(
            bad in lower_label
            for bad in [
                "profit payment", "profit rate",
                "indicative profit rates",
                "savings accounts",
            ]
        ):
            current_account = label
            print(f"[RateSheet] New savings account at row {idx}: {current_account}")
            continue

        # 2) Under a current account, capture payment + rate
        if current_account and rate:
            # skip header-like labels
            if any(h in lower_label for h in ["profit payment", "profit rate"]):
                continue

            if rate.replace(".", "", 1).isdigit():
                payment = label or ""

                # Original question (long form)
                q = f"What is the profit rate for {current_account}"
                if payment:
                    q += f" with {payment} profit payment?"
                else:
                    q += "?"
                a = f"The profit rate for {current_account}"
                if payment:
                    a += f" with {payment} profit payment is {rate}."
                else:
                    a += f" is {rate}."

                base_doc = {
                    "sheet": sheet_name,
                    "question": q,
                    "answer": a,
                    "meta": {
                        "type": "savings_rate",
                        "excel_row": int(idx),
                        "account": current_account,
                        "payment": payment,
                        "rate": rate,
                    },
                }
                rows.append(base_doc)

                # Duplicate product-centric doc if we have a short code
                short_code = SAVINGS_SHORT_CODES.get(current_account)
                if short_code:
                    q2 = f"What is the profit rate for {short_code} ({current_account})"
                    if payment:
                        q2 += f" with {payment} profit payment?"
                    else:
                        q2 += "?"
                    # You can reuse the same answer text
                    doc2 = {
                        "sheet": sheet_name,
                        "question": q2,
                        "answer": a,
                        "meta": {
                            "type": "savings_rate_alias",
                            "excel_row": int(idx),
                            "account": current_account,
                            "short_code": short_code,
                            "payment": payment,
                            "rate": rate,
                        },
                    }
                    rows.append(doc2)

    print(f"\n[RateSheet] Total savings-account rows found (including aliases): {len(rows)}\n")
    return rows


def extract_term_deposits_from_rate_sheet(sheet_name: str, df: pd.DataFrame):
    """
    Right side of the Rate Sheet:
    term deposits with 3-column tables:
    Tenor | Payout | Profit Rate.
    Also emits alias docs for common short names.
    """
    COL_TENOR = 5
    COL_PAYOUT = 6
    COL_RATE = 8

    TERM_SHORT_CODES = {
        "Short Notice Deposit Receipt (SNDR)": "SNDR",
        "NUST Waqaar Account - Senior Citizen - Term Deposit": "WAA TD",
        "NUST Bachat Account -Individual/Corporate and\n\n                               Value Plus Term Deposit*": "Bachat TD",
        "NUST Maximiser - Term Deposit": "Maximiser TD",
        "NUST Sahar - Term Deposit": "Sahar TD",
        "Term Deposit": "Term Deposit",
    }

    current_product = None
    rows = []

    print(f"\n[RateSheet] Scanning rows for term deposits (right) in '{sheet_name}'...\n")

    for idx, row in df.iterrows():
        val5 = str(row[COL_TENOR]).strip() if COL_TENOR in row else ""
        val6 = str(row[COL_PAYOUT]).strip() if COL_PAYOUT in row else ""
        val8 = str(row[COL_RATE]).strip() if COL_RATE in row else ""

        if val5.lower().startswith("nan"):
            val5 = ""
        if val6.lower().startswith("nan"):
            val6 = ""
        if val8.lower().startswith("nan"):
            val8 = ""

        lower5 = val5.lower()

        # Switch to generic "Term Deposit" block when hitting TERM DEPOSITS
        if "term deposits" in lower5 and "nust" not in lower5:
            current_product = "Term Deposit"
            print(f"[RateSheet] Switching to generic term-deposit block at row {idx}")
            continue

        # Detect specific term-deposit product headers
        if val5 and not val8 and any(
            kw in lower5
            for kw in [
                "short notice deposit receipt",  # SNDR
                "waqaar account - senior citizen - term deposit",
                "bachat account -individual/corporate",
                "maximiser - term deposit",
                "sahar - term deposit",
            ]
        ):
            current_product = val5
            print(f"[RateSheet] New term deposit product at row {idx}: {current_product}")
            continue

        # Under a current product, capture tenor/payout/rate
        if current_product and val5 and val8:
            if val8.replace(".", "", 1).isdigit():
                tenor = val5
                payout = val6
                rate = val8

                # Original question
                q = f"What is the profit rate for {current_product} for {tenor}?"
                a = f"The profit rate for {current_product} for {tenor} is {rate}"
                if payout:
                    a += f", with payout at {payout}."
                else:
                    a += "."

                base_doc = {
                    "sheet": sheet_name,
                    "question": q,
                    "answer": a,
                    "meta": {
                        "type": "term_deposit_rate",
                        "excel_row": int(idx),
                        "product": current_product,
                        "tenor": tenor,
                        "payout": payout,
                        "rate": rate,
                    },
                }
                rows.append(base_doc)

                # Alias doc
                short_code = TERM_SHORT_CODES.get(current_product)
                if short_code:
                    q2 = f"What is the profit rate for {short_code} ({current_product}) for {tenor}?"
                    doc2 = {
                        "sheet": sheet_name,
                        "question": q2,
                        "answer": a,
                        "meta": {
                            "type": "term_deposit_rate_alias",
                            "excel_row": int(idx),
                            "product": current_product,
                            "short_code": short_code,
                            "tenor": tenor,
                            "payout": payout,
                            "rate": rate,
                        },
                    }
                    rows.append(doc2)

    print(f"\n[RateSheet] Total term-deposit rows found (including aliases): {len(rows)}\n")
    return rows


# ----------------- Main Excel extraction ----------------- #

def extract_knowledge_from_excel(path: str):
    """
    Test extractor:
    - Reads all sheets from the given Excel file path
    - Writes QA pairs to bank_knowledge_test.json
    - Processes 'Rate Sheet July 1 2024' and 'Main' first, then others.
    """
    sheets = pd.read_excel(path, sheet_name=None, header=None)

    print("Sheets found:", list(sheets.keys()))

    knowledge = []

    preferred_first = [
        "Rate Sheet July 1 2024",
        "Rate Sheet July 1, 2024",
        "Rate Sheet July 1",
        "Rate Sheet",
        "Main",
    ]

    ordered_sheet_names = []
    for name in preferred_first:
        if name in sheets and name not in ordered_sheet_names:
            ordered_sheet_names.append(name)

    for name in sheets.keys():
        if name not in ordered_sheet_names:
            ordered_sheet_names.append(name)

    for sheet_name in ordered_sheet_names:
        df = sheets[sheet_name]
        print(f"\n========== Processing sheet: {sheet_name} ==========\n")

        # Special handling for catalog sheet
        if sheet_name.lower() == "main":
            main_qas = extract_products_from_main_sheet(sheet_name, df)
            print(f"[Main] QAs produced: {len(main_qas)}")
            knowledge.extend(main_qas)

        # Special handling for Rate Sheet(s): extract savings + term deposits
        if sheet_name in [
            "Rate Sheet July 1 2024",
            "Rate Sheet July 1, 2024",
            "Rate Sheet July 1",
            "Rate Sheet",
        ]:
            savings_qas = extract_savings_accounts_from_rate_sheet(sheet_name, df)
            term_qas = extract_term_deposits_from_rate_sheet(sheet_name, df)
            print(
                f"[RateSheet] QAs produced from savings: {len(savings_qas)}, "
                f"from term deposits: {len(term_qas)}"
            )
            knowledge.extend(savings_qas)
            knowledge.extend(term_qas)

        # Generic QA extraction for every sheet
        current_question = None
        answer_lines = []

        for _, row in df.iterrows():
            cells = [str(cell).strip() for cell in row if pd.notna(cell)]
            if not cells:
                continue

            text = " ".join(cells)

            if is_question(text):
                if current_question and answer_lines:
                    knowledge.append(
                        {
                            "sheet": sheet_name,
                            "question": current_question,
                            "answer": " ".join(answer_lines),
                        }
                    )

                current_question = text
                answer_lines = []
            else:
                if current_question:
                    answer_lines.append(text)

        if current_question and answer_lines:
            knowledge.append(
                {
                    "sheet": sheet_name,
                    "question": current_question,
                    "answer": " ".join(answer_lines),
                }
            )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, indent=2, ensure_ascii=False)

    print(
        f"[test_extract_knowledge] Extraction complete. "
        f"{len(knowledge)} QA pairs saved to {output_file}."
    )


if __name__ == "__main__":
    extract_knowledge_from_excel("NUST Bank-Product-Knowledge.xlsx")
