"""Native Text (Mode B) Surgical Editing Module with Single-Baseline Reflow.

Performs targeted surgical text replacement in native PDFs using PyMuPDF (fitz).
Preserves font, bold/italic flags, size, color, baseline, visual alignment, and reflows
spans on the exact same baseline to eliminate blank gaps without touching unrelated lines.
"""

from typing import Dict, Any, List, Tuple, Optional
import pymupdf as fitz  # PyMuPDF
from pdf.font_manager import fit_text_in_bbox, get_text_width, resolve_font_name
from pdf.analyzer import color_int_to_rgb


def get_all_page_spans(page_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts all text spans from a PyMuPDF page dictionary."""
    spans = []
    for block in page_dict.get("blocks", []):
        if block.get("type") == 0:  # Text block
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("text", "").strip():
                        spans.append(span)
    return spans


def edit_native_text_pdf(
    input_pdf_path: str,
    output_pdf_path: str,
    operations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Applies surgical native text replacements with single-baseline reflow.

    Returns execution status and metadata.
    """
    doc = fitz.open(input_pdf_path)
    modified_ops = []

    # Group operations by page
    ops_by_page: Dict[int, List[Dict[str, Any]]] = {}
    for op in operations:
        if op.get("target_type") == "native_text":
            page_num = op["page"]
            ops_by_page.setdefault(page_num, []).append(op)

    for page_num, ops in ops_by_page.items():
        page = doc[page_num]
        page_dict = page.get_text("dict")
        all_spans = get_all_page_spans(page_dict)

        processed_baselines = set()

        for op in ops:
            target_span = op["span"]
            tb = target_span["bbox"]
            op_new_text = op["new_value"]

            origin = target_span.get("origin", [tb[0], tb[3]])
            baseline_y = origin[1]

            # Unique key for this baseline
            baseline_key = (page_num, round(baseline_y, 1))
            if baseline_key in processed_baselines:
                continue
            processed_baselines.add(baseline_key)

            # Find all spans on the exact same baseline (y within 2.5pt)
            same_line_spans = [
                s for s in all_spans
                if abs(s.get("origin", [s["bbox"][0], s["bbox"][3]])[1] - baseline_y) < 2.5
            ]

            if not same_line_spans:
                same_line_spans = [target_span]

            # Sort spans by left X coordinate
            same_line_spans.sort(key=lambda s: s["bbox"][0])

            # Build line items
            line_items = []
            for span in same_line_spans:
                sb = span["bbox"]

                # Check if this span is a target span for an operation
                matching_op = None
                for candidate_op in ops:
                    cb = candidate_op["span"]["bbox"]
                    if not (sb[2] <= cb[0] or sb[0] >= cb[2] or sb[3] <= cb[1] or sb[1] >= cb[3]):
                        matching_op = candidate_op
                        break

                if matching_op:
                    new_val = matching_op["new_value"]
                    orig_font = matching_op["font"]
                    orig_size = matching_op["size"]
                    flags = matching_op.get("flags", span.get("flags", 0))
                    color = matching_op.get("color", [0, 0, 0])

                    target_width = matching_op["bbox"][2] - matching_op["bbox"][0]
                    fits, res_font, res_size, _ = fit_text_in_bbox(
                        text=new_val,
                        original_font_name=orig_font,
                        original_font_size=orig_size,
                        target_width=target_width,
                        flags=flags
                    )

                    new_w = get_text_width(new_val, res_font, res_size, flags)
                    line_items.append({
                        "is_target": True,
                        "text": new_val,
                        "font": res_font,
                        "size": res_size,
                        "color": color,
                        "width": new_w,
                        "span": span
                    })
                    modified_ops.append(matching_op["field"])
                else:
                    span_text = span.get("text", "")
                    flags = span.get("flags", 0)
                    font_name = resolve_font_name(span.get("font", "helv"), flags)
                    font_size = span.get("size", 12.0)
                    color = span.get("color", [0, 0, 0])
                    if isinstance(color, int):
                        color = color_int_to_rgb(color)

                    span_w = get_text_width(span_text, font_name, font_size, flags)
                    line_items.append({
                        "is_target": False,
                        "text": span_text,
                        "font": font_name,
                        "size": font_size,
                        "color": color,
                        "width": span_w,
                        "span": span
                    })

            # Calculate baseline insertion points with exact gap & space preservation
            first_s = same_line_spans[0]
            first_orig = first_s.get("origin", [first_s["bbox"][0], first_s["bbox"][3]])
            x_cursor = first_orig[0]

            for idx, item in enumerate(line_items):
                if idx > 0:
                    prev_s = same_line_spans[idx - 1]
                    curr_s = same_line_spans[idx]
                    prev_item = line_items[idx - 1]

                    orig_gap = curr_s["bbox"][0] - prev_s["bbox"][2]
                    min_gap = max(0.0, orig_gap)

                    # Ensure minimum space gap if adjacent spans don't contain explicit leading/trailing spaces
                    prev_text = prev_item["text"]
                    curr_text = item["text"]
                    if prev_text and curr_text and not prev_text.endswith(" ") and not curr_text.startswith(" ") and not prev_text.endswith(":") and not curr_text.startswith(","):
                        space_w = get_text_width(" ", prev_item["font"], prev_item["size"])
                        min_gap = max(min_gap, space_w)

                    x_cursor += min_gap

                item["insert_point"] = (x_cursor, baseline_y)
                x_cursor += item["width"]

            # Redact ONLY spans on this specific baseline
            for s in same_line_spans:
                page.add_redact_annot(fitz.Rect(s["bbox"]), fill=(1, 1, 1))

            page.apply_redactions(images=0, graphics=0)

            # Re-insert spans on this baseline
            for item in line_items:
                if item["text"]:  # Insert non-empty strings
                    point = fitz.Point(item["insert_point"])
                    page.insert_text(
                        point=point,
                        text=item["text"],
                        fontname=item["font"],
                        fontsize=item["size"],
                        color=item["color"]
                    )

    doc.save(output_pdf_path, garbage=4, deflate=True)
    doc.close()

    return {
        "success": True,
        "modified_fields": modified_ops,
        "output_path": output_pdf_path
    }
