"""Test line reflow targeted text mutation on offer letter PDF."""

import os
from pdf.analyzer import analyze_pdf
from pdf.field_resolver import build_edit_plan
from pdf.text_editor import edit_native_text_pdf
from pdf.validator import validate_pdf_edit
from tests.create_offer_letter_pdf import create_offer_letter_pdf

def test_offer_letter_edit():
    pdf_path = create_offer_letter_pdf("test_offer_letter_in.pdf")
    out_path = "test_offer_letter_out.pdf"

    analysis = analyze_pdf(pdf_path)
    plan = build_edit_plan(analysis, {"UI/UX Design Intern": "DATABASE"})

    print(f"Plan success: {plan.get('success')}")
    print(f"Operations count: {len(plan.get('operations', []))}")

    res = edit_native_text_pdf(pdf_path, out_path, plan["operations"])
    print(f"Edit res: {res}")

    val = validate_pdf_edit(pdf_path, out_path, plan["operations"])
    print(f"Validation: {val}")

    # Inspect text in edited PDF
    edited_analysis = analyze_pdf(out_path)
    print("\n--- EDITED TEXT SPANS ---")
    for s in edited_analysis["text_spans"]:
        print(f"Page {s['page']}: '{s['text']}' at bbox {s['bbox']}")

if __name__ == "__main__":
    test_offer_letter_edit()
