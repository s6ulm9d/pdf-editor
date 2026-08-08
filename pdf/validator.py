"""Post-Edit Structural & Asset Preservation Validator.

Validates that non-target content (images, logos, vectors, page geometry,
unrelated text) remains 100% untouched after PDF editing operations.
"""

from typing import Dict, Any, List
from pdf.analyzer import analyze_pdf
from pdf.visual_diff import compare_pdf_visuals


def validate_pdf_edit(
    orig_pdf_path: str,
    edited_pdf_path: str,
    operations: List[Dict[str, Any]],
    enable_visual_diff: bool = True
) -> Dict[str, Any]:
    """Runs comprehensive structural, asset, and visual validation on modified PDF."""
    orig_analysis = analyze_pdf(orig_pdf_path)
    edited_analysis = analyze_pdf(edited_pdf_path)

    passed = True
    failures = []

    # 1. Page count & geometry preservation
    pages_before = orig_analysis["total_pages"]
    pages_after = edited_analysis["total_pages"]
    if pages_before != pages_after:
        passed = False
        failures.append(f"Page count changed: before={pages_before}, after={pages_after}")

    page_geometry_preserved = True
    for p1, p2 in zip(orig_analysis["pages"], edited_analysis["pages"]):
        if p1["width"] != p2["width"] or p1["height"] != p2["height"] or p1["rotation"] != p2["rotation"]:
            page_geometry_preserved = False
            passed = False
            failures.append(f"Page {p1['page_num']} geometry altered.")

    # 2. Image assets preservation
    images_before = orig_analysis["total_images"]
    images_after = edited_analysis["total_images"]
    images_preserved = (images_before == images_after)

    if not images_preserved:
        passed = False
        failures.append(f"Image count changed: before={images_before}, after={images_after}")

    # Check image hashes
    orig_hashes = sorted([img["hash"] for img in orig_analysis["images"]])
    edited_hashes = sorted([img["hash"] for img in edited_analysis["images"]])
    if orig_hashes != edited_hashes and orig_analysis["mode"] != "MODE_A_ACROFORM":
        images_preserved = False
        passed = False
        failures.append("Embedded image content/hashes altered.")

    # 3. Vector graphics preservation
    drawings_before = orig_analysis["total_drawings"]
    drawings_after = edited_analysis["total_drawings"]

    # Redactions add fill shapes per redacted span on a line; allow drawing count change up to 4 * len(operations)
    expected_extra_drawings = len(operations) * 4
    vectors_preserved = (drawings_after >= drawings_before and (drawings_after - drawings_before) <= expected_extra_drawings) or (drawings_before == drawings_after)

    if not vectors_preserved and orig_analysis["mode"] != "MODE_A_ACROFORM":
        passed = False
        failures.append(f"Unexpected vector drawing count change: before={drawings_before}, after={drawings_after}")

    # 4. Unrelated text preservation outside target bboxes & modified line baselines
    target_bboxes = []
    target_words = set()
    modified_lines_by_page: Dict[int, List[float]] = {}

    for op in operations:
        page_n = op.get("page", 0)
        if "bbox" in op:
            target_bboxes.append(op["bbox"])
        if "span" in op and "bbox" in op["span"]:
            target_bboxes.append(op["span"]["bbox"])
            modified_lines_by_page.setdefault(page_n, []).append(op["span"]["bbox"][1])
        if "line_bbox" in op:
            target_bboxes.append(op["line_bbox"])

        for val in (op.get("old_value", ""), op.get("new_value", ""), op.get("field", "")):
            for w in str(val).lower().split():
                target_words.add(w.strip(":;.,\"'()[]"))

    def get_non_target_text(spans: List[Dict[str, Any]], bboxes: List[List[float]]) -> List[str]:
        non_target = []
        buf = 5.0
        for s in spans:
            p_num = s.get("page", 0)
            sy1 = s["bbox"][1]

            # Check if span is on a modified line baseline
            is_on_modified_line = False
            for mod_y in modified_lines_by_page.get(p_num, []):
                if abs(sy1 - mod_y) < 6.0:
                    is_on_modified_line = True
                    break
            if is_on_modified_line:
                continue

            sb = s["bbox"]
            is_target = False
            for tb in bboxes:
                if not (sb[2] <= (tb[0] - buf) or sb[0] >= (tb[2] + buf) or sb[3] <= (tb[1] - buf) or sb[1] >= (tb[3] + buf)):
                    is_target = True
                    break
            if not is_target:
                words = s["text"].strip().split()
                clean_words = [w for w in words if w.lower().strip(":;.,\"'()[]") not in target_words]
                if clean_words:
                    non_target.append(" ".join(clean_words))
        return non_target

    orig_non_target = get_non_target_text(orig_analysis["text_spans"], target_bboxes)
    edited_non_target = get_non_target_text(edited_analysis["text_spans"], target_bboxes)

    norm_orig_text = " ".join(" ".join(orig_non_target).split())
    norm_edited_text = " ".join(" ".join(edited_non_target).split())

    unexpected_text_changes = 0
    if norm_orig_text != norm_edited_text and orig_analysis["mode"] == "MODE_B_NATIVE_TEXT":
        unexpected_text_changes = 1
        passed = False
        failures.append("Unintended changes detected in unrelated native text.")

    # 5. Visual regression check
    visual_report = None
    if enable_visual_diff:
        visual_report = compare_pdf_visuals(orig_pdf_path, edited_pdf_path, operations)
        if not visual_report["passed"]:
            passed = False
            failures.append("Visual regression validation detected unexpected changes outside target fields.")

    return {
        "passed": passed,
        "pages_before": pages_before,
        "pages_after": pages_after,
        "images_before": images_before,
        "images_after": images_after,
        "images_preserved": images_preserved,
        "page_geometry_preserved": page_geometry_preserved,
        "vectors_preserved": vectors_preserved,
        "requested_changes": len(operations),
        "unexpected_text_changes": unexpected_text_changes,
        "unsafe_changes": len(failures),
        "failures": failures,
        "visual_diff": visual_report
    }
