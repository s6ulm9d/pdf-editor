"""Field Resolver & Instruction Parsing Module.

Converts human instructions or dictionary field maps into structured,
unambiguous edit plans with bounding boxes, page numbers, and font specs.
"""

import re
from typing import Dict, Any, List, Optional
from pdf.analyzer import analyze_pdf


def parse_natural_language_instruction(instruction: str) -> Dict[str, str]:
    """Parses simple natural language instructions into key-value change requests.

    Example: "Change name to Sairaj and duration to 1 Month" -> {"name": "Sairaj", "duration": "1 Month"}
    """
    changes = {}
    pattern = r'(?:change|set|update)\s+(?:the\s+)?([a-zA-Z0-9_\s]+?)\s+(?:to|as|=)\s+(["\'][^"\']+["\']|\S+)'
    matches = re.findall(pattern, instruction, re.IGNORECASE)

    for field, value in matches:
        clean_field = field.strip().lower()
        clean_val = value.strip('"\'')
        changes[clean_field] = clean_val

    return changes


def find_matching_spans(
    field_key: str,
    spans: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Locates matching text spans in native text for a requested field key using strict priority rules.

    Priority 1: Exact span text match
    Priority 2: Multi-span consecutive text match (e.g. "UI/UX" + " Design Intern")
    Priority 3: Label prefix match (e.g. span is "Name: John Doe")
    Priority 4: Adjacent span value after standalone label ("Name:")
    Priority 5: Substring match
    """
    field_lower = field_key.strip().lower()
    field_clean = field_lower.rstrip(":")

    # Priority 1: Exact text match
    exact_matches = []
    for idx, span in enumerate(spans):
        text_lower = span["text"].strip().lower()
        if text_lower == field_lower or text_lower == field_clean:
            exact_matches.append({"span": span, "match_type": "exact_text", "index": idx})

    if exact_matches:
        return exact_matches

    # Priority 2: Multi-span consecutive text match
    multi_span_matches = []
    n = len(spans)
    for i in range(n):
        combined = ""
        combo_spans = []
        for j in range(i, min(n, i + 4)):
            if j > i:
                prev_s = spans[j - 1]
                curr_s = spans[j]
                if curr_s["page"] != prev_s["page"] or abs(curr_s["bbox"][1] - prev_s["bbox"][1]) > 25.0:
                    break
            combo_spans.append(spans[j])
            combined += spans[j]["text"]

            clean_combined = combined.strip().lower()
            if clean_combined == field_lower or clean_combined == field_clean or clean_combined.replace("  ", " ") == field_clean:
                multi_span_matches.append({
                    "span": combo_spans[0],
                    "combo_spans": combo_spans,
                    "match_type": "multi_span_exact",
                    "index": i
                })
                break

    if multi_span_matches:
        return multi_span_matches

    # Priority 3: Label prefix match e.g. "Name: John Doe"
    label_matches = []
    for idx, span in enumerate(spans):
        text_lower = span["text"].strip().lower()
        if text_lower.startswith(field_clean + ":") or text_lower.startswith(field_clean + " :"):
            label_matches.append({"span": span, "match_type": "label_prefix", "index": idx})

    if label_matches:
        return label_matches

    # Priority 4: Next adjacent span value after standalone label "Name:"
    for idx, span in enumerate(spans):
        text_clean = span["text"].strip().lower().rstrip(":")
        if text_clean == field_clean:
            if idx + 1 < len(spans):
                next_span = spans[idx + 1]
                return [{"span": next_span, "match_type": "value_after_label", "index": idx + 1, "label_span": span}]

    # Priority 5: Substring match
    sub_matches = []
    for idx, span in enumerate(spans):
        text_lower = span["text"].strip().lower()
        if field_clean in text_lower:
            sub_matches.append({"span": span, "match_type": "contains_label", "index": idx})

    return sub_matches


def check_bbox_overlap(
    bbox: List[float],
    images: List[Dict[str, Any]],
    page_num: int
) -> bool:
    """Checks if a bounding box overlaps with any embedded image on the given page."""
    x0, y0, x1, y1 = bbox

    for img in images:
        if img.get("page") != page_num:
            continue
        img_bbox = img.get("bbox")
        if not img_bbox:
            continue

        ix0, iy0, ix1, iy1 = img_bbox
        # Check intersection
        if not (x1 <= ix0 or x0 >= ix1 or y1 <= iy0 or y0 >= iy1):
            return True
    return False


def build_edit_plan(
    analysis: Dict[str, Any],
    changes: Dict[str, str]
) -> Dict[str, Any]:
    """Builds a structured edit plan for the requested field changes.

    Enforces Ambiguity Rule and Overlap Checks.
    """
    mode = analysis["mode"]
    spans = analysis["text_spans"]
    images = analysis["images"]
    form_fields = analysis.get("form_fields", [])

    operations = []
    ambiguous_fields = []
    missing_fields = []
    unsafe_fields = []

    for field_key, new_val in changes.items():
        # Mode A: AcroForm matching
        if mode == "MODE_A_ACROFORM":
            matched_form = None
            for ff in form_fields:
                if ff["name"].lower() == field_key.lower() or field_key.lower() in ff["name"].lower():
                    matched_form = ff
                    break
            if matched_form:
                operations.append({
                    "field": field_key,
                    "target_type": "acroform",
                    "form_name": matched_form["name"],
                    "old_value": matched_form["value"],
                    "new_value": new_val,
                    "editing_method": "MODE_A_ACROFORM"
                })
                continue

        # Mode B: Native Text matching
        matches = find_matching_spans(field_key, spans)

        if len(matches) == 0:
            missing_fields.append(field_key)
            continue

        for matched_info in matches:
            combo_spans = matched_info.get("combo_spans")
            if combo_spans:
                # Handle multi-span match: first span gets new_val, rest get ""
                for s_idx, matched_span in enumerate(combo_spans):
                    page_num = matched_span["page"]
                    bbox = matched_span["bbox"]
                    x0, y0, x1, y1 = bbox
                    target_val = new_val if s_idx == 0 else ""

                    operations.append({
                        "field": field_key,
                        "target_type": "native_text",
                        "page": page_num,
                        "span": matched_span,
                        "bbox": bbox,
                        "line_bbox": matched_span.get("line_bbox", bbox),
                        "old_value": matched_span["text"],
                        "new_value": target_val,
                        "font": matched_span["font"],
                        "size": matched_span["size"],
                        "color": matched_span["color"],
                        "origin": matched_span.get("origin"),
                        "editing_method": "MODE_B_NATIVE_TEXT"
                    })
            else:
                matched_span = matched_info["span"]
                page_num = matched_span["page"]
                bbox = matched_span["bbox"]
                x0, y0, x1, y1 = bbox

                # Get page width
                page_width = 595.0
                if "pages" in analysis and len(analysis["pages"]) > page_num:
                    page_width = analysis["pages"][page_num].get("width", 595.0)

                # Find distance to next text span to the right on the same line
                right_spans = [
                    s for s in spans
                    if s["page"] == page_num and s != matched_span and s["bbox"][0] >= x1 + 2.0 and abs(s["bbox"][1] - y0) < 6.0
                ]

                if right_spans:
                    right_limit = min(s["bbox"][0] for s in right_spans) - 2.0
                else:
                    line_right = matched_span.get("line_bbox", bbox)[2]
                    right_limit = max(line_right, page_width - 36.0)

                available_width = max(x1 - x0, right_limit - x0)
                target_bbox = [x0, y0, x0 + available_width, y1]

                orig_text = matched_span["text"]
                replacement_val = new_val

                if ":" in orig_text:
                    parts = orig_text.split(":", 1)
                    label_part = parts[0] + ":"
                    if not new_val.lower().startswith(label_part.lower()):
                        replacement_val = f"{label_part} {new_val.strip()}"

                if check_bbox_overlap(bbox, images, page_num):
                    unsafe_fields.append({
                        "field": field_key,
                        "reason": "Target bounding box overlaps embedded image asset."
                    })
                    continue

                operations.append({
                    "field": field_key,
                    "target_type": "native_text",
                    "page": page_num,
                    "span": matched_span,
                    "bbox": target_bbox,
                    "line_bbox": matched_span.get("line_bbox", bbox),
                    "old_value": orig_text,
                    "new_value": replacement_val,
                    "font": matched_span["font"],
                    "size": matched_span["size"],
                    "color": matched_span["color"],
                    "origin": matched_span.get("origin"),
                    "editing_method": "MODE_B_NATIVE_TEXT"
                })

    if ambiguous_fields:
        return {
            "success": False,
            "status": "ambiguous",
            "message": f"Multiple possible matching locations detected for field(s): {[f['field'] for f in ambiguous_fields]}",
            "candidates": ambiguous_fields,
            "requires_manual_review": True
        }

    if missing_fields:
        return {
            "success": False,
            "status": "missing_fields",
            "message": f"Requested field(s) not found in PDF: {missing_fields}",
            "missing_fields": missing_fields,
            "requires_manual_review": True
        }

    if unsafe_fields:
        return {
            "success": False,
            "status": "unsafe_edit",
            "message": f"Editing field(s) would damage PDF assets: {unsafe_fields}",
            "unsafe_fields": unsafe_fields,
            "requires_manual_review": True
        }

    return {
        "success": True,
        "mode": mode,
        "operations": operations
    }
