import io
import pdfplumber
from docx import Document
from .clean import clean_text
from dataclasses import dataclass
from typing import Optional

# Configuration constants
MAX_RESUME_CHARS = 15000  # Truncate extremely long resumes
MIN_TEXT_LENGTH = 200     # Minimum viable text length
SCANNED_PDF_THRESHOLD = 100  # Characters per page threshold for scanned detection


@dataclass
class ExtractionResult:
    """Result of text extraction with metadata."""
    text: str
    success: bool
    char_count: int
    page_count: int
    truncated: bool
    warnings: list[str]
    file_type: str
    
    @property
    def is_likely_scanned(self) -> bool:
        """Check if PDF appears to be scanned (low text per page)."""
        if self.page_count == 0:
            return False
        return self.char_count / self.page_count < SCANNED_PDF_THRESHOLD


def extract_pdf(file_bytes: bytes) -> ExtractionResult:
    """Extract text from a PDF with detailed metadata."""
    warnings = []
    text_parts = []
    page_count = 0
    
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
        
        raw_text = "\n".join(text_parts)
        char_count = len(raw_text)
        
        # Check for scanned PDF
        if page_count > 0 and char_count / page_count < SCANNED_PDF_THRESHOLD:
            warnings.append("⚠️ This PDF appears to be scanned or image-based. Text extraction may be incomplete.")
        
        # Truncate if too long
        truncated = False
        if char_count > MAX_RESUME_CHARS:
            raw_text = raw_text[:MAX_RESUME_CHARS]
            truncated = True
            warnings.append(f"⚠️ Resume was truncated to {MAX_RESUME_CHARS:,} characters for processing.")
        
        cleaned_text = clean_text(raw_text)
        
        # Check extraction success
        success = len(cleaned_text) >= MIN_TEXT_LENGTH
        if not success:
            warnings.append("❌ Very little text extracted. The PDF may be scanned, corrupted, or protected.")
        
        return ExtractionResult(
            text=cleaned_text,
            success=success,
            char_count=len(cleaned_text),
            page_count=page_count,
            truncated=truncated,
            warnings=warnings,
            file_type="pdf"
        )
        
    except Exception as e:
        return ExtractionResult(
            text="",
            success=False,
            char_count=0,
            page_count=0,
            truncated=False,
            warnings=[f"❌ PDF extraction failed: {str(e)}"],
            file_type="pdf"
        )


def extract_docx(file_bytes: bytes) -> ExtractionResult:
    """Extract text from a DOCX file with detailed metadata."""
    warnings = []
    
    try:
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        raw_text = "\n".join(paragraphs)
        char_count = len(raw_text)
        
        # Truncate if too long
        truncated = False
        if char_count > MAX_RESUME_CHARS:
            raw_text = raw_text[:MAX_RESUME_CHARS]
            truncated = True
            warnings.append(f"⚠️ Resume was truncated to {MAX_RESUME_CHARS:,} characters for processing.")
        
        cleaned_text = clean_text(raw_text)
        
        # Check extraction success
        success = len(cleaned_text) >= MIN_TEXT_LENGTH
        if not success:
            warnings.append("❌ Very little text extracted. The document may be empty or corrupted.")
        
        return ExtractionResult(
            text=cleaned_text,
            success=success,
            char_count=len(cleaned_text),
            page_count=len(doc.sections),
            truncated=truncated,
            warnings=warnings,
            file_type="docx"
        )
        
    except Exception as e:
        return ExtractionResult(
            text="",
            success=False,
            char_count=0,
            page_count=0,
            truncated=False,
            warnings=[f"❌ DOCX extraction failed: {str(e)}"],
            file_type="docx"
        )


def extract_txt(file_bytes: bytes) -> ExtractionResult:
    """Extract text from a plain text file."""
    warnings = []
    
    try:
        raw_text = file_bytes.decode("utf-8", errors="ignore")
        char_count = len(raw_text)
        
        # Truncate if too long
        truncated = False
        if char_count > MAX_RESUME_CHARS:
            raw_text = raw_text[:MAX_RESUME_CHARS]
            truncated = True
            warnings.append(f"⚠️ Resume was truncated to {MAX_RESUME_CHARS:,} characters for processing.")
        
        cleaned_text = clean_text(raw_text)
        
        success = len(cleaned_text) >= MIN_TEXT_LENGTH
        if not success:
            warnings.append("❌ Very little text found in the file.")
        
        return ExtractionResult(
            text=cleaned_text,
            success=success,
            char_count=len(cleaned_text),
            page_count=1,
            truncated=truncated,
            warnings=warnings,
            file_type="txt"
        )
        
    except Exception as e:
        return ExtractionResult(
            text="",
            success=False,
            char_count=0,
            page_count=0,
            truncated=False,
            warnings=[f"❌ Text extraction failed: {str(e)}"],
            file_type="txt"
        )


def extract_any(filename: str, file_bytes: bytes) -> ExtractionResult:
    """Extract text from PDF/DOCX/TXT based on extension."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_pdf(file_bytes)
    if name.endswith(".docx"):
        return extract_docx(file_bytes)
    # treat as plain text
    return extract_txt(file_bytes)


# Legacy compatibility function
def extract_text_simple(filename: str, file_bytes: bytes) -> str:
    """Simple extraction returning just text (backward compatibility)."""
    result = extract_any(filename, file_bytes)
    return result.text
