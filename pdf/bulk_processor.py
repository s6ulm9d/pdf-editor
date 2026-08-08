"""Bulk PDF Generation Engine.

Parses Excel (.xlsx) or CSV (.csv) data files and generates customized PDFs
for every row in bulk using explicit field-to-column mappings, packaged into a ZIP archive.
"""

import os
import re
import csv
import zipfile
from typing import Dict, Any, List, Optional
import openpyxl

from pdf.analyzer import analyze_pdf
from pdf.field_resolver import build_edit_plan
from pdf.text_editor import edit_native_text_pdf
from pdf.validator import validate_pdf_edit
from pdf.email_sender import send_email_with_pdf_attachment


def sanitize_filename(name: str) -> str:
    """Sanitizes a string to be a safe filesystem filename."""
    clean = re.sub(r'[\\/*?:"<>|]', '_', name).strip()
    return clean if clean else "document"


def parse_data_file(file_path: str) -> List[Dict[str, str]]:
    """Parses a CSV or Excel file into a list of row dictionaries."""
    rows = []
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                clean_row = {k.strip(): str(v).strip() for k, v in r.items() if k and v is not None}
                if any(clean_row.values()):
                    rows.append(clean_row)
    elif ext in (".xlsx", ".xls"):
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet = wb.active
        header = None
        for row in sheet.iter_rows(values_only=True):
            if not row:
                continue
            if header is None:
                header = [str(c).strip() if c is not None else f"col_{idx}" for idx, c in enumerate(row)]
            else:
                row_dict = {}
                for idx, cell in enumerate(row):
                    if idx < len(header) and cell is not None:
                        val = str(cell).strip()
                        if val:
                            row_dict[header[idx]] = val
                if row_dict:
                    rows.append(row_dict)
        wb.close()
    else:
        raise ValueError(f"Unsupported data file extension: {ext}. Only .csv and .xlsx are supported.")

    return rows


def process_bulk_pdf_edits(
    template_pdf_path: str,
    data_file_path: str,
    output_dir: str,
    field_mappings: Optional[Dict[str, str]] = None,
    send_email_toggle: bool = False,
    email_column_name: Optional[str] = None,
    email_subject: str = "Your Document Offer Letter",
    email_body: str = "Dear Candidate,\n\nPlease find attached your offer letter PDF.\n\nBest Regards,\nHR Team",
    smtp_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generates bulk PDFs for each row in the data file using optional field mappings and sends emails if enabled."""
    os.makedirs(output_dir, exist_ok=True)
    data_rows = parse_data_file(data_file_path)

    if not data_rows:
        return {
            "success": False,
            "message": "Data file is empty or contains no valid rows.",
            "generated_count": 0
        }

    generated_pdfs = []
    failed_rows = []
    sent_emails_count = 0
    zip_path = os.path.join(output_dir, "bulk_edited_pdfs.zip")

    smtp_cfg = smtp_config or {}

    # Analyze base template once
    template_analysis = analyze_pdf(template_pdf_path)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for idx, row_dict in enumerate(data_rows, start=1):
            # Construct changes map using field_mappings if supplied
            row_changes = {}
            if field_mappings:
                for pdf_field, col_header in field_mappings.items():
                    if col_header in row_dict:
                        row_changes[pdf_field] = row_dict[col_header]
            else:
                row_changes = row_dict

            if not row_changes:
                row_changes = row_dict

            # Determine output PDF filename based on Ref ID or Name column
            ref_id_val = None
            for key, val in row_changes.items():
                k_lower = str(key).lower()
                v_str = str(val)
                if "ref" in k_lower or "id" in k_lower or "code" in k_lower or v_str.startswith("ALG-"):
                    ref_id_val = v_str
                    break

            if not ref_id_val:
                for key, val in row_dict.items():
                    if "ref" in str(key).lower() or "id" in str(key).lower() or str(val).startswith("ALG-"):
                        ref_id_val = str(val)
                        break

            if not ref_id_val:
                name_val = row_changes.get("Naman Dwivedi") or row_changes.get("name") or row_changes.get("Name")
                ref_id_val = name_val if name_val else f"row_{idx}"

            safe_basename = sanitize_filename(ref_id_val)
            out_pdf_name = f"{safe_basename}.pdf"
            out_pdf_path = os.path.join(output_dir, out_pdf_name)

            # Build edit plan for this row
            plan = build_edit_plan(template_analysis, row_changes)

            if not plan.get("success"):
                failed_rows.append({
                    "row": idx,
                    "changes": row_changes,
                    "reason": plan.get("message", "Edit plan generation failed.")
                })
                continue

            # Mutate PDF
            edit_res = edit_native_text_pdf(template_pdf_path, out_pdf_path, plan["operations"])

            if edit_res.get("success"):
                val_res = validate_pdf_edit(template_pdf_path, out_pdf_path, plan["operations"])
                zipf.write(out_pdf_path, arcname=out_pdf_name)

                email_status = None
                if send_email_toggle and email_column_name and email_column_name in row_dict:
                    recipient_email = row_dict[email_column_name].strip()
                    if recipient_email and "@" in recipient_email:
                        email_res = send_email_with_pdf_attachment(
                            to_email=recipient_email,
                            subject=email_subject,
                            body_text=email_body,
                            attachment_pdf_path=out_pdf_path,
                            smtp_host=smtp_cfg.get("host", "smtp.gmail.com"),
                            smtp_port=int(smtp_cfg.get("port", 587)),
                            sender_email=smtp_cfg.get("sender_email", ""),
                            sender_password=smtp_cfg.get("sender_password", "")
                        )
                        email_status = email_res
                        if email_res.get("success"):
                            sent_emails_count += 1

                generated_pdfs.append({
                    "row": idx,
                    "filename": out_pdf_name,
                    "filepath": out_pdf_path,
                    "validation": val_res,
                    "email_status": email_status
                })
            else:
                failed_rows.append({
                    "row": idx,
                    "changes": row_changes,
                    "reason": "PDF native text mutation failed."
                })

    return {
        "success": len(generated_pdfs) > 0,
        "zip_path": zip_path,
        "total_rows": len(data_rows),
        "generated_count": len(generated_pdfs),
        "failed_count": len(failed_rows),
        "sent_emails_count": sent_emails_count,
        "generated_pdfs": generated_pdfs,
        "failed_rows": failed_rows
    }
