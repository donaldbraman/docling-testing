#!/usr/bin/env python3
"""
Bounding box coordinate transformation utilities.

Handles coordinate system conversions between different frameworks:
- ocrmac: bottom-origin (y=0 at bottom, y=1 at top) with normalized coordinates
- PyMuPDF: top-origin (y=0 at top, y increases downward) with absolute coordinates
"""


def ocrmac_to_pymupdf(
    x0_norm: float,
    y0_norm: float,
    x1_norm: float,
    y1_norm: float,
    page_width: float,
    page_height: float,
) -> tuple[float, float, float, float]:
    """Convert ocrmac normalized bottom-origin coordinates to PyMuPDF absolute top-origin.

    Args:
        x0_norm: Left edge (normalized 0-1)
        y0_norm: Bottom edge in ocrmac (normalized 0-1, y=0 at bottom)
        x1_norm: Right edge (normalized 0-1)
        y1_norm: Top edge in ocrmac (normalized 0-1, y=0 at bottom)
        page_width: Page width in points
        page_height: Page height in points

    Returns:
        Tuple of (x0, y0, x1, y1) in PyMuPDF coordinates:
        - x0, x1: absolute horizontal coordinates in points
        - y0: top edge in PyMuPDF (y=0 at top)
        - y1: bottom edge in PyMuPDF (y=0 at top)

    Example:
        >>> # ocrmac box at bottom of page (y0=0.0, y1=0.1)
        >>> ocrmac_to_pymupdf(0.1, 0.0, 0.9, 0.1, 612, 792)
        (61.2, 712.8, 550.8, 792.0)  # PyMuPDF box near bottom (y0=712.8, y1=792)

        >>> # ocrmac box at top of page (y0=0.9, y1=1.0)
        >>> ocrmac_to_pymupdf(0.1, 0.9, 0.9, 1.0, 612, 792)
        (61.2, 0.0, 550.8, 79.2)  # PyMuPDF box near top (y0=0, y1=79.2)
    """
    # Scale to absolute coordinates
    x0 = x0_norm * page_width
    x1 = x1_norm * page_width

    # Flip y-coordinates: ocrmac y=0 (bottom) → PyMuPDF y=height (bottom)
    # ocrmac y1 (top of box) → PyMuPDF y0 (top of box)
    # ocrmac y0 (bottom of box) → PyMuPDF y1 (bottom of box)
    y0_pymupdf = (1 - y1_norm) * page_height
    y1_pymupdf = (1 - y0_norm) * page_height

    return (x0, y0_pymupdf, x1, y1_pymupdf)


def pymupdf_to_ocrmac(
    x0: float, y0: float, x1: float, y1: float, page_width: float, page_height: float
) -> tuple[float, float, float, float]:
    """Convert PyMuPDF absolute top-origin coordinates to ocrmac normalized bottom-origin.

    Args:
        x0: Left edge in points
        y0: Top edge in PyMuPDF (y=0 at top)
        x1: Right edge in points
        y1: Bottom edge in PyMuPDF (y=0 at top)
        page_width: Page width in points
        page_height: Page height in points

    Returns:
        Tuple of (x0_norm, y0_norm, x1_norm, y1_norm) in ocrmac coordinates:
        - x0_norm, x1_norm: normalized horizontal coordinates (0-1)
        - y0_norm: bottom edge in ocrmac (normalized 0-1, y=0 at bottom)
        - y1_norm: top edge in ocrmac (normalized 0-1, y=0 at bottom)
    """
    # Normalize to 0-1
    x0_norm = x0 / page_width
    x1_norm = x1 / page_width

    # Flip y-coordinates: PyMuPDF y=0 (top) → ocrmac y=1 (top)
    y0_norm = 1 - (y1 / page_height)  # PyMuPDF bottom → ocrmac bottom
    y1_norm = 1 - (y0 / page_height)  # PyMuPDF top → ocrmac top

    return (x0_norm, y0_norm, x1_norm, y1_norm)
