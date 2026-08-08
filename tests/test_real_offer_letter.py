"""Test targeted text mutation on real offer letter layout."""

import fitz
from pdf.analyzer import analyze_pdf
from pdf.field_resolver import build_edit_plan
from pdf.text_editor import edit_native_text_pdf
from pdf.validator import validate_pdf_edit


def create_full_offer_letter_pdf(path: str = "offer_letter_real.pdf") -> str:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Header title
    page.insert_text(fitz.Point(180, 80), "INTERNSHIP OFFER LETTER", fontname="hebo", fontsize=18)

    # Metadata block
    page.insert_text(fitz.Point(50, 130), "Date - 15-07-2026", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 150), "Dear Naman Dwivedi", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 170), "Ref.: ALG-UI-0106", fontname="helv", fontsize=11)

    # Paragraph 1
    page.insert_text(fitz.Point(50, 210), "Congratulations! We are pleased to inform you that you have been selected for the position of", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 230), "UI/UX Design Intern", fontname="hebo", fontsize=11)
    page.insert_text(fitz.Point(170, 230), " at ", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(185, 230), "Algoryx Systems.", fontname="hebo", fontsize=11)
    page.insert_text(fitz.Point(280, 230), " We were impressed by your creativity, attention to", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 250), "detail, and passion for designing intuitive digital experiences. We are excited to welcome you to our", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 270), "team.", fontname="helv", fontsize=11)

    # Paragraph 2
    page.insert_text(fitz.Point(50, 310), "As a ", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(75, 310), "UI/UX Design Intern", fontname="hebo", fontsize=11)
    page.insert_text(fitz.Point(185, 310), ", you will work on real-world product design projects involving user", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 330), "research, wireframing, user flows, prototyping, high-fidelity interface design, responsive layouts,", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 350), "and design systems. You will collaborate closely with developers to create modern, user-centric", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 370), "web experiences while gaining practical industry exposure.", fontname="helv", fontsize=11)

    # Details table
    page.insert_text(fitz.Point(50, 420), "Internship Details", fontname="hebo", fontsize=14)

    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(50, 440, 545, 580))
    shape.draw_line(fitz.Point(50, 470), fitz.Point(545, 470))
    shape.draw_line(fitz.Point(180, 440), fitz.Point(180, 580))
    shape.finish(color=(0.7, 0.7, 0.7), width=1)
    shape.commit()

    page.insert_text(fitz.Point(60, 460), "Position", fontname="hebo", fontsize=11)
    page.insert_text(fitz.Point(190, 460), "UI/UX Design Intern", fontname="helv", fontsize=11)

    page.insert_text(fitz.Point(60, 490), "Duration", fontname="hebo", fontsize=11)
    page.insert_text(fitz.Point(190, 490), "1 Month", fontname="helv", fontsize=11)

    # Footer section
    page.insert_text(fitz.Point(50, 620), "We welcome you to Algoryx Systems.", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 680), "Best Regards,", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 700), "HR Team", fontname="hebo", fontsize=11)
    page.insert_text(fitz.Point(50, 715), "Algoryx Systems", fontname="helv", fontsize=11)

    doc.save(path)
    doc.close()
    return path


def test_full_offer_letter():
    pdf_in = create_full_offer_letter_pdf("offer_letter_test_in.pdf")
    pdf_out = "offer_letter_test_out.pdf"

    analysis = analyze_pdf(pdf_in)
    plan = build_edit_plan(analysis, {"UI/UX Design Intern": "DATABASE"})

    print("=== PLAN ===")
    print(f"Success: {plan.get('success')}")
    print(f"Operations: {len(plan.get('operations', []))}")

    res = edit_native_text_pdf(pdf_in, pdf_out, plan["operations"])
    print(f"Mutation Result: {res}")

    val = validate_pdf_edit(pdf_in, pdf_out, plan["operations"])
    print(f"Validation Result: {val}")

    out_analysis = analyze_pdf(pdf_out)
    print("\n=== EXTRACTED TEXT FROM EDITED PDF ===")
    full_text = ""
    for s in out_analysis["text_spans"]:
        full_text += f"{s['text']}\n"
    print(full_text)

    # Assert critical contents are NOT erased!
    assert "Date - 15-07-2026" in full_text, "Date header was erased!"
    assert "Dear Naman Dwivedi" in full_text, "Name header was erased!"
    assert "Ref.: ALG-UI-0106" in full_text, "Ref header was erased!"
    assert "Congratulations! We are pleased to inform you that you have been selected for the position of" in full_text, "Paragraph 1 text was erased!"
    assert "DATABASE" in full_text, "DATABASE replacement text was not found!"

if __name__ == "__main__":
    test_full_offer_letter()
