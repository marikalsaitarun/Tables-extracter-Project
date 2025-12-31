import json
import sqlite3
import re
import io
import os
from PyPDF2 import PdfReader
from google import genai
from PIL import Image
import fitz
import csv 
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-2.5-flash"

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def clean(name):
    return re.sub(r"\W+", "_", name.lower())

def process_pdf(pdf_path, json_out="tables.json", db_path="test.db"):
    reader = PdfReader(pdf_path)
    doc = fitz.open(pdf_path)
    all_pages = []

    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        pdf_page = doc.load_page(i - 1)
        pix = pdf_page.get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        prompt = f"""
                Extract all tables from this PDF page.
                Return ONLY valid JSON in this format:

                {{
                "page": {i},
                "tables": [
                    {{
                    "headers": ["col1", "col2"],
                    "rows": [
                        ["v1", "v2"]
                    ]
                    }}
                ]
                }}

                Rules:
                - If no tables exist, return "tables": []
                - Headers must align with rows
                - Do not add explanations
                """

        response = client.models.generate_content(
            model=MODEL,
            contents=[prompt, text, img],
            config={"response_mime_type": "application/json"}
        )

        all_pages.append(json.loads(response.text))

    # Save JSON
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, indent=2)

    # Stage 2: SQLite
    conn = sqlite3.connect(db_path) # db is being generated here
    cur = conn.cursor()

    for page in all_pages:
        for t_idx, table in enumerate(page["tables"], start=1):
            table_name = f"page_{page['page']}_table_{t_idx}"
            columns = [clean(h) for h in table["headers"]]

            col_sql = ", ".join([f'"{c}" TEXT' for c in columns])
            cur.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({col_sql})')

            for row in table["rows"]:
                placeholders = ",".join(["?"] * len(columns))
                cur.execute(
                    f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                    row
                )
        # ✅ ADD: CSV writer (minimal)
            csv_file = f"{table_name}.csv"
            writer = csv.writer(open(csv_file, "w", newline="", encoding="utf-8"))
            writer.writerow(table["headers"])

            for row in table["rows"]:
                placeholders = ",".join(["?"] * len(columns))
                cur.execute(
                    f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                    row
                )

                # ✅ ADD: write row to CSV
                writer.writerow(row)


    conn.commit()
    conn.close()

    return all_pages, json_out, db_path



