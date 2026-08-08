"""End-to-End API & PDF Verification Script.

Tests the full FastAPI end-to-end pipeline with an actual PDF document containing
background images, logos, decorative vectors, and multiple text blocks.
"""

import os
import json
from fastapi.testclient import TestClient
from main import app
from pdf.analyzer import analyze_pdf
from tests.pdf_fixtures import create_composite_pdf_with_assets

TEST_PDF_PATH = "e2e_input.pdf"


def run_e2e_verification():
    print("=== STARTING END-TO-END E2E VERIFICATION ===")

    # 1. Create realistic composite PDF with background, logo, vectors, target text & unrelated text
    create_composite_pdf_with_assets(TEST_PDF_PATH)
    initial_analysis = analyze_pdf(TEST_PDF_PATH)

    print(f"[1] Created Test PDF: {TEST_PDF_PATH}")
    print(f"    Mode: {initial_analysis['mode']}")
    print(f"    Total Pages: {initial_analysis['total_pages']}")
    print(f"    Total Images: {initial_analysis['total_images']}")
    print(f"    Total Vectors: {initial_analysis['total_drawings']}")

    client = TestClient(app)

    # 2. Test /pdf/analyze endpoint
    with open(TEST_PDF_PATH, "rb") as f:
        response = client.post("/pdf/analyze", files={"file": ("input.pdf", f, "application/pdf")})

    assert response.status_code == 200, f"Analyze failed: {response.text}"
    analyze_res = response.json()
    print("[2] POST /pdf/analyze response: SUCCESS")
    print(f"    Detected {len(analyze_res['text_spans'])} text spans and {analyze_res['total_images']} images.")

    # 3. Test /pdf/edit endpoint with targeted field changes
    changes = {
        "name": "Sairaj Developer",
        "date": "09/08/2026"
    }

    with open(TEST_PDF_PATH, "rb") as f:
        edit_response = client.post(
            "/pdf/edit",
            files={"file": ("input.pdf", f, "application/pdf")},
            data={"changes_json": json.dumps(changes)}
        )

    assert edit_response.status_code == 200, f"Edit failed: {edit_response.text}"
    edit_res = edit_response.json()
    print("[3] POST /pdf/edit response: SUCCESS")
    print(f"    Output File: {edit_res['output_file']}")
    print(f"    Validation Passed: {edit_res['validation']['passed']}")
    print(f"    Images Preserved: {edit_res['validation']['images_preserved']}")
    print(f"    Geometry Preserved: {edit_res['validation']['page_geometry_preserved']}")
    print(f"    Unexpected Changes: {edit_res['validation']['unexpected_text_changes']}")

    # 4. Download and inspect generated output PDF
    download_url = edit_res["download_url"]
    dl_response = client.get(download_url)
    assert dl_response.status_code == 200, f"Download failed: {dl_response.status_code}"

    output_pdf_path = "e2e_output.pdf"
    with open(output_pdf_path, "wb") as out_f:
        out_f.write(dl_response.content)

    print(f"[4] Downloaded edited output PDF to: {output_pdf_path}")

    # 5. Re-analyze output PDF to confirm fidelity
    post_analysis = analyze_pdf(output_pdf_path)
    assert post_analysis["total_pages"] == initial_analysis["total_pages"]
    assert post_analysis["total_images"] == initial_analysis["total_images"]

    # Verify requested text actually changed in output PDF
    text_content = ""
    for span in post_analysis["text_spans"]:
        text_content += span["text"] + " "

    assert "Sairaj Developer" in text_content, "Target name was not updated in output PDF!"
    assert "09/08/2026" in text_content, "Target date was not updated in output PDF!"
    assert "Authorized by the Board of Examiners." in text_content, "Unrelated text was damaged!"

    print("\n[OK] E2E VERIFICATION COMPLETED SUCCESSFULLY!")
    print("[OK] Output PDF opens correctly")
    print("[OK] Requested fields updated")
    print("[OK] Background images and logo intact")
    print("[OK] Unrelated text untouched")


if __name__ == "__main__":
    run_e2e_verification()
