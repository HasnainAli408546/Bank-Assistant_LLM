import pandas as pd
import json

# Excel file
excel_file = "NUST Bank-Product-Knowledge.xlsx"

# Output JSON (this will overwrite previous file)
output_file = "bank_knowledge.json"


def is_question(text):
    """
    Detect whether a text line is a question
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
        "eligibility"
    )

    if text.endswith("?"):
        return True

    if text.startswith(question_words):
        return True

    for k in faq_keywords:
        if k in text:
            return True

    return False


def extract_knowledge():

    sheets = pd.read_excel(excel_file, sheet_name=None, header=None)

    knowledge = []

    for sheet_name, df in sheets.items():

        current_question = None
        answer_lines = []

        for _, row in df.iterrows():

            # collect non-empty cells
            cells = [str(cell).strip() for cell in row if pd.notna(cell)]

            if not cells:
                continue

            text = " ".join(cells)

            if is_question(text):

                # save previous QA
                if current_question and answer_lines:
                    knowledge.append({
                        "sheet": sheet_name,
                        "question": current_question,
                        "answer": " ".join(answer_lines)
                    })

                # start new question
                current_question = text
                answer_lines = []

            else:

                if current_question:
                    answer_lines.append(text)

        # save last QA in sheet
        if current_question and answer_lines:
            knowledge.append({
                "sheet": sheet_name,
                "question": current_question,
                "answer": " ".join(answer_lines)
            })

    # overwrite JSON file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, indent=2, ensure_ascii=False)

    print(f"Extraction complete. {len(knowledge)} QA pairs saved.")


if __name__ == "__main__":
    extract_knowledge()