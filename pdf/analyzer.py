"""PDF Analyzer Module.

Inspects PDF structure, pages, dimensions, images, hashes, vector objects, forms,
text spans, font metadata, and candidate editable fields.
"""

import hashlib
from typing import Dict, Any, List
import fitz  # PyMuPDF
from pypdf import PdfReader
from pdf.classifier import classify_pdf


def get_image_hash(image_bytes: bytes) -> str:
    """Returns SHA-256 hash of raw image content."""
    return hashlib.sha256(image_bytes).hexdigest()


def color_int_to_rgb(color_int: int) -> List[float]:
    """Converts PyMuPDF sRGB int color to [r, g, b] float tuple (0.0 to 1.0)."""
    r = ((color_int >> 16) & 255) / 255.0
    g = ((color_int >> 8) & 255) / 255.0
    b = (color_int & 255) / 255.0
    return [r, g, b]


def analyze_pdf(pdf_path: str) -> Dict[str, Any]:
    """Performs deep structural analysis of a PDF document."""
    classification = classify_pdf(pdf_path)
    doc = fitz.open(pdf_path)

    pages_info = []
    all_images = []
    all_text_spans = []
    all_vector_drawings_count = 0
    candidate_fields = []
    fonts_used = set()

    for page_idx, page in enumerate(doc):
        rect = page.rect
        page_width, page_height = rect.width, rect.height
        rotation = page.rotation

        # Drawings (vector objects)
        drawings = page.get_drawings()
        all_vector_drawings_count += len(drawings)

        # Images
        image_list = page.get_images(full=True)
        page_images = []
        for img_info in image_list:
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                img_hash = get_image_hash(image_bytes)
                img_dict = {
                    "page": page_idx,
                    "xref": xref,
                    "width": base_image["width"],
                    "height": base_image["height"],
                    "ext": base_image["ext"],
                    "hash": img_hash
                }
                page_images.append(img_dict)
                all_images.append(img_dict)
            except Exception:
                pass

        # Text extraction with dict layout
        page_dict = page.get_text("dict")
        page_spans = []

        for block in page_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    line_bbox = line.get("bbox")
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if not span_text.strip():
                            continue

                        font_name = span.get("font", "Helvetica")
                        font_size = span.get("size", 12.0)
                        color_int = span.get("color", 0)
                        color_rgb = color_int_to_rgb(color_int)
                        span_bbox = list(span.get("bbox", [0, 0, 0, 0]))
                        origin = list(span.get("origin", [span_bbox[0], span_bbox[3]]))

                        fonts_used.add(font_name)

                        span_data = {
                            "page": page_idx,
                            "text": span_text,
                            "bbox": span_bbox,
                            "line_bbox": list(line_bbox) if line_bbox else span_bbox,
                            "font": font_name,
                            "size": font_size,
                            "color": color_rgb,
                            "flags": span.get("flags", 0),
                            "origin": origin
                        }
                        page_spans.append(span_data)
                        all_text_spans.append(span_data)

                        # Candidate field heuristics (e.g. key-value format or standalone value)
                        if ":" in span_text or len(span_text.strip()) < 50:
                            candidate_fields.append({
                                "text": span_text,
                                "page": page_idx,
                                "bbox": span_bbox,
                                "font": font_name,
                                "size": font_size
                            })

        pages_info.append({
            "page_num": page_idx,
            "width": page_width,
            "height": page_height,
            "rotation": rotation,
            "image_count": len(page_images),
            "drawing_count": len(drawings),
            "span_count": len(page_spans)
        })

    # AcroForm extraction from PyMuPDF and pypdf
    form_fields = []
    seen_field_names = set()

    for page in doc:
        for w in page.widgets():
            w_name = w.field_name
            if w_name and w_name not in seen_field_names:
                seen_field_names.add(w_name)
                form_fields.append({
                    "name": w_name,
                    "value": str(w.field_value or ""),
                    "type": str(w.field_type)
                })

    try:
        reader = PdfReader(pdf_path)
        if reader.fields:
            for field_name, field_obj in reader.fields.items():
                if field_name not in seen_field_names:
                    seen_field_names.add(field_name)
                    form_fields.append({
                        "name": field_name,
                        "value": str(field_obj.get("/V", "")),
                        "type": str(field_obj.get("/FT", ""))
                    })
    except Exception:
        pass

    doc.close()

    return {
        "classification": classification,
        "mode": classification["mode"],
        "pages": pages_info,
        "total_pages": len(pages_info),
        "images": all_images,
        "total_images": len(all_images),
        "total_drawings": all_vector_drawings_count,
        "form_fields": form_fields,
        "text_spans": all_text_spans,
        "candidate_fields": candidate_fields,
        "fonts": list(fonts_used),
        "warnings": []
    }
