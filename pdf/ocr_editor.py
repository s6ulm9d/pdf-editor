"""OCR Fallback (Mode C) Editing Module.

For scanned/image-only PDFs: uses PyTesseract to locate target text bounding boxes,
validates confidence, patches the target region, and overlays replacement text.
"""

from typing import Dict, Any, List
import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import pytesseract


MIN_OCR_CONFIDENCE = 70.0  # 70% threshold required for safe automated edit


def edit_scanned_pdf(
    input_pdf_path: str,
    output_pdf_path: str,
    operations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Edits scanned PDF pages using OCR bounding box detection.

    If OCR confidence is low or target cannot be confidently localized, refuses edit.
    """
    doc = fitz.open(input_pdf_path)

    for op in operations:
        page_num = op.get("page", 0)
        page = doc[page_num]

        # Render page to high-DPI image (300 DPI)
        pix = page.get_pixmap(dpi=300)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if pix.n == 4:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)

        # Run Tesseract OCR with detailed data
        try:
            ocr_data = pytesseract.image_to_data(img_np, output_type=pytesseract.Output.DICT)
        except Exception as e:
            doc.close()
            return {
                "success": False,
                "error": f"OCR engine error: {str(e)}. Tesseract may not be installed or configured.",
                "requires_manual_review": True
            }

        target_text = op.get("old_value", op.get("field", "")).lower()
        new_text = op["new_value"]

        # Search for matching words and check confidence
        matched_indices = []
        n_boxes = len(ocr_data["text"])
        for i in range(n_boxes):
            word = ocr_data["text"][i].strip()
            conf = float(ocr_data["conf"][i])

            if word and word.lower() in target_text or target_text in word.lower():
                if conf < MIN_OCR_CONFIDENCE:
                    doc.close()
                    return {
                        "success": False,
                        "error": f"Low OCR confidence ({conf:.1f}% < {MIN_OCR_CONFIDENCE}%) for target text '{word}'. Manual review required.",
                        "requires_manual_review": True
                    }
                matched_indices.append(i)

        if not matched_indices:
            doc.close()
            return {
                "success": False,
                "error": f"Target text '{target_text}' not detected with high confidence in scanned document.",
                "requires_manual_review": True
            }

        # Calculate bounding box in PDF point coordinates
        scale_x = page.rect.width / pix.width
        scale_y = page.rect.height / pix.height

        min_x = min(ocr_data["left"][i] for i in matched_indices)
        min_y = min(ocr_data["top"][i] for i in matched_indices)
        max_x = max(ocr_data["left"][i] + ocr_data["width"][i] for i in matched_indices)
        max_y = max(ocr_data["top"][i] + ocr_data["height"][i] for i in matched_indices)

        pdf_bbox = [
            min_x * scale_x,
            min_y * scale_y,
            max_x * scale_x,
            max_y * scale_y
        ]

        # Perform targeted redaction and text insertion on page
        rect = fitz.Rect(pdf_bbox)
        page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_NONE,
            graphics=fitz.PDF_REDACT_LINE_NONE
        )

        target_h = pdf_bbox[3] - pdf_bbox[1]
        font_size = max(8.0, target_h * 0.8)
        page.insert_text(
            point=fitz.Point(pdf_bbox[0], pdf_bbox[3] - 2.0),
            text=new_text,
            fontname="helv",
            fontsize=font_size,
            color=(0, 0, 0)
        )

    doc.save(output_pdf_path, garbage=4, deflate=True)
    doc.close()

    return {
        "success": True,
        "mode": "MODE_C_SCANNED",
        "output_path": output_pdf_path
    }
