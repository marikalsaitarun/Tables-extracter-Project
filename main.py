import streamlit as st
import tempfile
import json
from backend import process_pdf

st.set_page_config(page_title="PDF Table Extractor", layout="wide")

st.title("PDF Table Extractor (Gemini + SQLite)")

uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        pdf_path = tmp.name
        # print(pdf_path)

    if st.button(" Extract Tables"):
        with st.spinner("Processing PDF with Gemini..."):
            tables, json_path, db_path = process_pdf(pdf_path)

        st.success("Extraction completed!")

        # Show extracted tables
        for page in tables:
            st.subheader(f"Page {page['page']}")
            for idx, table in enumerate(page["tables"], start=1):
                st.write(f"Table {idx}")
                st.table(
                    {
                        h: [row[i] for row in table["rows"]]
                        for i, h in enumerate(table["headers"])
                    }
                )



