"""AcroForm (Mode A) Editing Module.

Mutates form fields in fillable PDFs while preserving non-target fields and page appearance.
"""

from typing import Dict, Any, List
from pypdf import PdfReader, PdfWriter


def edit_acroform_pdf(
    input_pdf_path: str,
    output_pdf_path: str,
    operations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Updates specified AcroForm fields in input_pdf_path and saves to output_pdf_path.

    Returns execution summary.
    """
    field_updates = {op["form_name"]: op["new_value"] for op in operations if op.get("target_type") == "acroform"}

    try:
        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()
        writer.append(reader)

        for page_idx, page in enumerate(writer.pages):
            writer.update_page_form_field_values(page, field_updates, auto_regenerate=True)

        with open(output_pdf_path, "wb") as f_out:
            writer.write(f_out)

        return {
            "success": True,
            "modified_fields": list(field_updates.keys()),
            "output_path": output_pdf_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
