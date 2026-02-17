import io
import pdfplumber
from docx import Document
from .clean import clean_text

def extract_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF (best-effort; scanned PDFs may return little/no text)."""
    text = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text.append(page.extract_text() or "")
    return clean_text("\n".join(text))

def extract_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file."""
    doc = Document(io.BytesIO(file_bytes))
    return clean_text("\n".join(p.text for p in doc.paragraphs))

def extract_any(filename: str, file_bytes: bytes) -> str:
    """Extract text from PDF/DOCX/TXT based on extension."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_pdf(file_bytes)
    if name.endswith(".docx"):
        return extract_docx(file_bytes)
    # treat as plain text
    return clean_text(file_bytes.decode("utf-8", errors="ignore"))
