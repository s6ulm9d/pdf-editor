"""PDF Classification Module.

Categorizes PDFs into Mode A (AcroForm), Mode B (Native Text), or Mode C (Scanned/Image).
"""

from enum import Enum
from typing import Dict, Any
import pymupdf as fitz  # PyMuPDF
from pypdf import PdfReader


class PDFMode(str, Enum):
    MODE_A_ACROFORM = "MODE_A_ACROFORM"
    MODE_B_NATIVE_TEXT = "MODE_B_NATIVE_TEXT"
    MODE_C_SCANNED = "MODE_C_SCANNED"


def classify_pdf(pdf_path: str) -> Dict[str, Any]:
    """Classifies a PDF file into MODE_A_ACROFORM, MODE_B_NATIVE_TEXT, or MODE_C_SCANNED.

    Returns detailed classification metadata.
    """
    mode = PDFMode.MODE_B_NATIVE_TEXT
    has_acroform = False
    total_native_text_chars = 0
    total_pages = 0
    total_images = 0

    # 1. Check Mode A (AcroForm) using pypdf & PyMuPDF
    try:
        reader = PdfReader(pdf_path)
        if reader.fields:
            has_acroform = True
    except Exception:
        pass

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    for page in doc:
        # Check PyMuPDF widgets/fields
        if list(page.widgets()):
            has_acroform = True

        # Extract native text
        text = page.get_text()
        total_native_text_chars += len(text.strip())

        # Count images
        total_images += len(page.get_images(full=True))

    doc.close()

    if has_acroform:
        mode = PDFMode.MODE_A_ACROFORM
    elif total_native_text_chars < 20 and total_images > 0:
        mode = PDFMode.MODE_C_SCANNED
    else:
        mode = PDFMode.MODE_B_NATIVE_TEXT

    return {
        "mode": mode,
        "has_acroform": has_acroform,
        "total_pages": total_pages,
        "total_native_text_chars": total_native_text_chars,
        "total_images": total_images
    }
