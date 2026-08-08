"""Test Bulk PDF Generation with explicit Field-to-Column Mappings and Email Dispatch."""

import os
import openpyxl
from pdf.bulk_processor import process_bulk_pdf_edits, parse_data_file
from pdf.email_sender import send_email_with_pdf_attachment
from tests.test_real_offer_letter import create_full_offer_letter_pdf

TEST_DIR = os.path.dirname(__file__)


def test_bulk_csv_with_mappings():
    template_pdf = create_full_offer_letter_pdf(os.path.join(TEST_DIR, "bulk_mapped_template.pdf"))
    csv_path = os.path.join(TEST_DIR, "bulk_mapped_data.csv")
    out_dir = os.path.join(TEST_DIR, "bulk_mapped_csv_out")

    # Create CSV file with custom header names
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("Candidate_Name,Reference_ID,Joining_Date,Role_Title,Candidate_Email\n")
        f.write("Rahul Sharma,ALG-UI-0107,16-07-2026,DATABASE,rahul@example.com\n")
        f.write("Priya Patel,ALG-UI-0108,17-07-2026,FRONTEND,priya@example.com\n")
        f.write("Aarav Mehta,ALG-UI-0109,18-07-2026,BACKEND,aarav@example.com\n")

    # Test parse_data_file
    rows = parse_data_file(csv_path)
    assert len(rows) == 3
    assert "Candidate_Name" in rows[0]

    # Field mappings: Target PDF Text -> Excel Column Header
    mappings = {
        "Naman Dwivedi": "Candidate_Name",
        "ALG-UI-0106": "Reference_ID",
        "15-07-2026": "Joining_Date",
        "UI/UX Design Intern": "Role_Title"
    }

    res = process_bulk_pdf_edits(template_pdf, csv_path, out_dir, field_mappings=mappings)

    assert res["success"] is True
    assert res["generated_count"] == 3
    assert os.path.exists(res["zip_path"])

    gen_names = [p["filename"] for p in res["generated_pdfs"]]
    assert "ALG-UI-0107.pdf" in gen_names
    assert "ALG-UI-0108.pdf" in gen_names
    assert "ALG-UI-0109.pdf" in gen_names


def test_bulk_excel_with_mappings():
    template_pdf = create_full_offer_letter_pdf(os.path.join(TEST_DIR, "bulk_mapped_template.pdf"))
    xlsx_path = os.path.join(TEST_DIR, "bulk_mapped_data.xlsx")
    out_dir = os.path.join(TEST_DIR, "bulk_mapped_xlsx_out")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Candidate_Name", "Reference_ID", "Joining_Date", "Role_Title", "Candidate_Email"])
    ws.append(["Aarav Mehta", "ALG-UI-0201", "20-07-2026", "BACKEND", "aarav@example.com"])
    ws.append(["Ananya Sen", "ALG-UI-0202", "21-07-2026", "FULLSTACK", "ananya@example.com"])
    ws.append(["Karan Kapoor", "ALG-UI-0203", "22-07-2026", "DEVOPS", "karan@example.com"])
    wb.save(xlsx_path)

    mappings = {
        "Naman Dwivedi": "Candidate_Name",
        "ALG-UI-0106": "Reference_ID",
        "15-07-2026": "Joining_Date",
        "UI/UX Design Intern": "Role_Title"
    }

    res = process_bulk_pdf_edits(
        template_pdf,
        xlsx_path,
        out_dir,
        field_mappings=mappings,
        send_email_toggle=True,
        email_column_name="Candidate_Email"
    )

    assert res["success"] is True
    assert res["generated_count"] == 3
    assert os.path.exists(res["zip_path"])


def test_email_sender_missing_creds():
    pdf_path = create_full_offer_letter_pdf(os.path.join(TEST_DIR, "email_dummy.pdf"))
    res = send_email_with_pdf_attachment(
        to_email="test@example.com",
        subject="Test Offer Letter",
        body_text="Test Body",
        attachment_pdf_path=pdf_path,
        sender_email="",
        sender_password=""
    )
    assert res["success"] is False
    assert "Missing SMTP sender credentials" in res["error"]
