import fitz  # PyMuPDF
import re
from pathlib import Path


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract full text from a PDF file."""
    doc = fitz.open(pdf_path)
    full_text = []
    for page in doc:
        full_text.append(page.get_text())
    doc.close()
    return "\n".join(full_text)


def extract_metadata(pdf_path: str) -> dict:
    """Extract basic metadata from PDF."""
    doc = fitz.open(pdf_path)
    meta = doc.metadata
    doc.close()
    return {
        "title": meta.get("title", Path(pdf_path).stem),
        "pages": doc.page_count if not doc.is_closed else len(doc),
        "filename": Path(pdf_path).name,
    }


def clean_text(text: str) -> str:
    """Clean extracted text."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'Page \d+ of \d+', '', text)
    return text.strip()
