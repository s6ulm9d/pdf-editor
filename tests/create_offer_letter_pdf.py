"""Create sample offer letter PDF matching user's document layout."""

import fitz

def create_offer_letter_pdf(path: str = "test_offer_letter.pdf") -> str:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Title
    page.insert_text(fitz.Point(180, 100), "INTERNSHIP OFFER LETTER", fontname="hebo", fontsize=18)

    # Metadata
    page.insert_text(fitz.Point(50, 150), "Date - 15-07-2026", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 170), "Dear Naman Dwivedi", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(50, 190), "Ref.: ALG-UI-0106", fontname="helv", fontsize=11)

    # Paragraph 1 with inline bold span
    y1 = 230
    page.insert_text(fitz.Point(50, y1), "Congratulations! We are pleased to inform you that you have been selected for the position of ", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(480, y1), "UI/UX Design Intern", fontname="hebo", fontsize=11)

    y2 = 245
    page.insert_text(fitz.Point(50, y2), "at ", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(62, y2), "Algoryx Systems.", fontname="hebo", fontsize=11)
    page.insert_text(fitz.Point(155, y2), " We were impressed by your creativity, attention to", fontname="helv", fontsize=11)

    # Paragraph 2
    y3 = 290
    page.insert_text(fitz.Point(50, y3), "As a ", fontname="helv", fontsize=11)
    page.insert_text(fitz.Point(75, y3), "UI/UX Design Intern", fontname="hebo", fontsize=11)
    page.insert_text(fitz.Point(185, y3), ", you will work on real-world product design projects...", fontname="helv", fontsize=11)

    # Table section
    page.insert_text(fitz.Point(50, 360), "Internship Details", fontname="hebo", fontsize=14)

    # Table lines
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(50, 380, 545, 520))
    shape.draw_line(fitz.Point(50, 410), fitz.Point(545, 410))
    shape.draw_line(fitz.Point(180, 380), fitz.Point(180, 520))
    shape.finish(color=(0.7, 0.7, 0.7), width=1)
    shape.commit()

    # Table cell contents
    page.insert_text(fitz.Point(60, 400), "Position", fontname="hebo", fontsize=11)
    page.insert_text(fitz.Point(190, 400), "UI/UX Design Intern", fontname="helv", fontsize=11)

    page.insert_text(fitz.Point(60, 430), "Duration", fontname="hebo", fontsize=11)
    page.insert_text(fitz.Point(190, 430), "1 Month", fontname="helv", fontsize=11)

    doc.save(path)
    doc.close()
    return path

if __name__ == "__main__":
    create_offer_letter_pdf()
    print("Created test_offer_letter.pdf successfully.")
