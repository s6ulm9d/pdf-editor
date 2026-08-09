"""Visual Regression Validation Module.

Renders original and modified PDF pages, masks out requested target bounding boxes,
and computes pixel difference on non-target regions to detect unintended visual changes.
"""

from typing import Dict, Any, List
import pymupdf as fitz  # PyMuPDF
import cv2
import numpy as np


def compare_pdf_visuals(
    orig_pdf_path: str,
    mod_pdf_path: str,
    target_operations: List[Dict[str, Any]],
    max_allowed_pixel_diff: float = 2.0
) -> Dict[str, Any]:
    """Compares rendered pages of orig_pdf and mod_pdf, ignoring target bboxes.

    Returns visual diff metrics.
    """
    orig_doc = fitz.open(orig_pdf_path)
    mod_doc = fitz.open(mod_pdf_path)

    len_orig = len(orig_doc)
    len_mod = len(mod_doc)

    if len_orig != len_mod:
        orig_doc.close()
        mod_doc.close()
        return {
            "passed": False,
            "reason": f"Page count mismatch: original has {len_orig} pages, modified has {len_mod} pages."
        }

    dpi = 150
    ops_by_page: Dict[int, List[List[float]]] = {}
    for op in target_operations:
        page_num = op.get("page", 0)
        bbox = op.get("bbox")
        if bbox:
            ops_by_page.setdefault(page_num, []).append(bbox)

    page_diffs = []
    overall_passed = True

    for page_idx in range(len(orig_doc)):
        p_orig = orig_doc[page_idx]
        p_mod = mod_doc[page_idx]

        pix_orig = p_orig.get_pixmap(dpi=dpi)
        pix_mod = p_mod.get_pixmap(dpi=dpi)

        img_orig = np.frombuffer(pix_orig.samples, dtype=np.uint8).reshape((pix_orig.height, pix_orig.width, pix_orig.n))
        img_mod = np.frombuffer(pix_mod.samples, dtype=np.uint8).reshape((pix_mod.height, pix_mod.width, pix_mod.n))

        if img_orig.shape != img_mod.shape:
            overall_passed = False
            page_diffs.append({
                "page": page_idx,
                "passed": False,
                "reason": "Rendered page dimension mismatch."
            })
            continue

        # Create mask for target bboxes (1 = valid region, 0 = target bbox to ignore)
        mask = np.ones((pix_orig.height, pix_orig.width), dtype=np.uint8)
        scale_x = pix_orig.width / p_orig.rect.width
        scale_y = pix_orig.height / p_orig.rect.height
        padding = 4  # 4 pixel margin around target bbox

        for bbox in ops_by_page.get(page_idx, []):
            x0 = max(0, int(bbox[0] * scale_x) - padding)
            y0 = max(0, int(bbox[1] * scale_y) - padding)
            x1 = min(pix_orig.width, int(bbox[2] * scale_x) + padding)
            y1 = min(pix_orig.height, int(bbox[3] * scale_y) + padding)

            mask[y0:y1, x0:x1] = 0

        # Compute difference in unmasked regions
        if pix_orig.n == 4:
            img_orig_rgb = cv2.cvtColor(img_orig, cv2.COLOR_RGBA2RGB)
            img_mod_rgb = cv2.cvtColor(img_mod, cv2.COLOR_RGBA2RGB)
        else:
            img_orig_rgb = img_orig
            img_mod_rgb = img_mod

        diff_img = cv2.absdiff(img_orig_rgb, img_mod_rgb)
        diff_gray = cv2.cvtColor(diff_img, cv2.COLOR_RGB2GRAY)

        unmasked_diff = diff_gray * mask
        valid_pixel_count = np.sum(mask)

        mean_diff = float(np.sum(unmasked_diff) / max(1, valid_pixel_count))
        page_passed = mean_diff <= max_allowed_pixel_diff

        if not page_passed:
            overall_passed = False

        page_diffs.append({
            "page": page_idx,
            "passed": page_passed,
            "mean_pixel_diff": round(mean_diff, 4)
        })

    orig_doc.close()
    mod_doc.close()

    return {
        "passed": overall_passed,
        "page_diffs": page_diffs
    }
