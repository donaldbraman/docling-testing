"""PDF manipulation utilities.

Centralizes PDF operations including grayscale conversion, image-only PDF creation,
and overlay generation.
"""

from pathlib import Path

import fitz  # PyMuPDF


def create_image_only_pdf(
    pdf_path: Path, output_path: Path, dpi: int = 300, grayscale: bool = True
) -> None:
    """Convert PDF to image-only PDF (removes text layer).

    Args:
        pdf_path: Path to input PDF
        output_path: Path for output PDF
        dpi: Resolution for rasterization (default: 300)
        grayscale: Convert to grayscale if True (default: True)

    Note:
        PyMuPDF's insert_image() may convert grayscale to RGB.
        Use check_pdf_colorspace() to verify output colorspace.
    """
    src_doc = fitz.open(str(pdf_path))
    img_doc = fitz.open()

    for page in src_doc:
        # Calculate scaling matrix for desired DPI
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        # Render page to image
        if grayscale:
            pix = page.get_pixmap(matrix=mat, colorspace="gray")
        else:
            pix = page.get_pixmap(matrix=mat)

        # Create new page and insert image
        img_page = img_doc.new_page(width=page.rect.width, height=page.rect.height)
        img_page.insert_image(img_page.rect, pixmap=pix)

    img_doc.save(str(output_path))
    img_doc.close()
    src_doc.close()


def check_pdf_colorspace(pdf_path: Path) -> str:
    """Check colorspace of PDF images.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Colorspace name (e.g., "DeviceGray", "DeviceRGB")
    """
    doc = fitz.open(str(pdf_path))
    if len(doc) == 0:
        doc.close()
        return "Empty PDF"

    page = doc[0]
    images = page.get_images()

    if not images:
        doc.close()
        return "No images"

    # Get colorspace of first image
    xref = images[0][0]
    pix = fitz.Pixmap(doc, xref)
    colorspace = pix.colorspace.name if pix.colorspace else "Unknown"
    doc.close()

    return colorspace


def create_color_overlay(
    pdf_path: Path,
    rectangles: list[tuple[int, fitz.Rect, tuple[float, float, float]]],
    output_path: Path,
) -> None:
    """Create PDF with colored rectangle overlays.

    Args:
        pdf_path: Path to input PDF
        rectangles: List of (page_num, rect, color) tuples where color is RGB (0-1)
        output_path: Path for output PDF
    """
    doc = fitz.open(str(pdf_path))

    for page_num, rect, color in rectangles:
        if page_num >= len(doc):
            continue
        page = doc[page_num]
        page.draw_rect(rect, color=color, width=1, fill=color, fill_opacity=0.2)

    doc.save(str(output_path))
    doc.close()


def extract_text_pymupdf(pdf_path: Path) -> str:
    """Extract all text from PDF using PyMuPDF.

    This gets embedded text only (what "select all" would get).

    Args:
        pdf_path: Path to PDF file

    Returns:
        Concatenated text from all pages
    """
    doc = fitz.open(str(pdf_path))
    text_parts = []

    for page in doc:
        text = page.get_text()
        if text.strip():
            text_parts.append(text)

    doc.close()
    return "".join(text_parts)


def get_pdf_page_count(pdf_path: Path) -> int:
    """Get number of pages in PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Number of pages
    """
    doc = fitz.open(str(pdf_path))
    count = len(doc)
    doc.close()
    return count
