"""PDF Test Fixture Generator.

Creates synthetic PDFs covering all 20 test scenarios including AcroForms, native text,
multi-page, scanned images, and composite PDFs with logos, background images, and vectors.
"""

import os
import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfWriter
from pypdf.annotations import Text, FreeText


def create_native_text_pdf(path: str) -> str:
    """Creates a basic native text PDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Title
    page.insert_text(fitz.Point(200, 100), "Certificate of Completion", fontname="hebo", fontsize=20, color=(0, 0.2, 0.6))
    # Target Name
    page.insert_text(fitz.Point(250, 200), "Name: John Doe", fontname="helv", fontsize=14, color=(0, 0, 0))
    # Target Date
    page.insert_text(fitz.Point(250, 250), "Date: 01/01/2026", fontname="helv", fontsize=12, color=(0.2, 0.2, 0.2))
    # Target Duration
    page.insert_text(fitz.Point(250, 300), "Duration: 6 Months", fontname="helv", fontsize=12, color=(0.2, 0.2, 0.2))
    # Unrelated Text
    page.insert_text(fitz.Point(100, 400), "This certificate confirms full completion of the advanced engineering course.", fontname="tiro", fontsize=11, color=(0.3, 0.3, 0.3))

    doc.save(path)
    doc.close()
    return path


def create_composite_pdf_with_assets(path: str) -> str:
    """Creates a rich composite PDF containing background image, logo, decorative vectors,

    multiple text blocks, target name, target date, and unrelated text.
    """
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    # 1. Background image asset
    bg_img = Image.new("RGB", (200, 200), color=(240, 245, 255))
    draw_bg = ImageDraw.Draw(bg_img)
    draw_bg.ellipse((20, 20, 180, 180), fill=(220, 230, 250))
    bg_path = "temp_bg.png"
    bg_img.save(bg_path)
    page.insert_image(fitz.Rect(50, 50, 550, 750), filename=bg_path)

    # 2. Logo image asset
    logo_img = Image.new("RGB", (100, 100), color=(255, 100, 50))
    draw_logo = ImageDraw.Draw(logo_img)
    draw_logo.rectangle((20, 20, 80, 80), fill=(255, 255, 255))
    logo_path = "temp_logo.png"
    logo_img.save(logo_path)
    page.insert_image(fitz.Rect(70, 70, 170, 170), filename=logo_path)

    # 3. Decorative vector graphics (lines & rectangles)
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(60, 60, 540, 740))
    shape.finish(color=(0.1, 0.3, 0.7), width=2)
    shape.draw_line(fitz.Point(100, 180), fitz.Point(500, 180))
    shape.finish(color=(0.8, 0.6, 0.1), width=1.5)
    shape.commit()

    # 4. Text blocks
    page.insert_text(fitz.Point(220, 120), "OFFICIAL CERTIFICATE", fontname="hebo", fontsize=22, color=(0.1, 0.2, 0.5))
    # Target Name (Centered)
    page.insert_text(fitz.Point(225, 280), "Name: Jane Smith", fontname="helv", fontsize=16, color=(0, 0, 0))
    # Target Date
    page.insert_text(fitz.Point(225, 340), "Date: 15/05/2026", fontname="helv", fontsize=14, color=(0.2, 0.2, 0.2))
    # Target Duration
    page.insert_text(fitz.Point(225, 400), "Duration: 3 Months", fontname="helv", fontsize=14, color=(0.2, 0.2, 0.2))
    # Unrelated Text
    page.insert_text(fitz.Point(120, 500), "Authorized by the Board of Examiners.", fontname="tiro", fontsize=12, color=(0.3, 0.3, 0.3))
    page.insert_text(fitz.Point(120, 530), "Certificate ID: CERT-2026-88942-X", fontname="cour", fontsize=10, color=(0.4, 0.4, 0.4))

    doc.save(path)
    doc.close()

    if os.path.exists(bg_path):
        os.remove(bg_path)
    if os.path.exists(logo_path):
        os.remove(logo_path)

    return path


def create_acroform_pdf(path: str) -> str:
    """Creates a fillable AcroForm PDF using PyMuPDF widgets."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text(fitz.Point(50, 100), "AcroForm Application", fontname="hebo", fontsize=18)

    # Widget 1: name
    widget1 = fitz.Widget()
    widget1.field_name = "name"
    widget1.field_value = "Original Name"
    widget1.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget1.rect = fitz.Rect(150, 150, 350, 180)
    page.add_widget(widget1)

    # Widget 2: date
    widget2 = fitz.Widget()
    widget2.field_name = "date"
    widget2.field_value = "01/01/2026"
    widget2.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget2.rect = fitz.Rect(150, 200, 350, 230)
    page.add_widget(widget2)

    doc.save(path)
    doc.close()
    return path


def create_ambiguous_text_pdf(path: str) -> str:
    """Creates a PDF with ambiguous (duplicate) text entries."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text(fitz.Point(100, 100), "Name: Alice Johnson", fontname="helv", fontsize=12)
    page.insert_text(fitz.Point(100, 200), "Name: Bob Williams", fontname="helv", fontsize=12)

    doc.save(path)
    doc.close()
    return path


def create_scanned_pdf(path: str) -> str:
    """Creates a scanned image-only PDF."""
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "Scanned Document", fill=(0, 0, 0))
    draw.text((50, 120), "Name: Scanned User", fill=(0, 0, 0))
    draw.text((50, 180), "Date: 10/10/2025", fill=(0, 0, 0))

    img_path = "temp_scan.png"
    img.save(img_path)

    doc = fitz.open()
    page = doc.new_page(width=600, height=400)
    page.insert_image(fitz.Rect(0, 0, 600, 400), filename=img_path)
    doc.save(path)
    doc.close()

    if os.path.exists(img_path):
        os.remove(img_path)
    return path


def create_multipage_pdf(path: str) -> str:
    """Creates a 3-page native text PDF."""
    doc = fitz.open()

    for p in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text(fitz.Point(50, 50), f"Page {p+1} Header", fontname="hebo", fontsize=16)
        page.insert_text(fitz.Point(50, 150), f"Name: Person Page {p+1}", fontname="helv", fontsize=12)
        page.insert_text(fitz.Point(50, 750), f"Footer for page {p+1}", fontname="tiro", fontsize=10)

    doc.save(path)
    doc.close()
    return path
