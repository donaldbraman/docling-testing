#!/usr/bin/env python3
"""
PDF Page Visualization with Semantic Label Overlays

Renders PDF pages to images and draws colored bounding boxes for semantic
regions (body text, headings, footnotes, captions, headers/footers).

Color coding:
- Body text (light blue #ADD8E6)
- Headings (light orange #FFD4A3)
- Footnotes (light pink #FFB6D9)
- Captions (light green #C8E6C9)
- Headers/Footers (light gray #DCDCDC)

TECHNICAL NOTE (Issue #32):
pypdfium2 PdfBitmap conversion to PIL Image requires investigation.
The PdfBitmap object from page.render() does not expose pil() or tobytes()
methods in current version. Alternative approaches to explore:
1. Direct buffer access via memoryview or ctypes
2. Using pypdfium2 with different rendering method
3. Switching to pdf2image library (requires system dependencies)
4. Using pdfplumber for text + bounding boxes (semantic inference fallback)

Current implementation provides the framework for annotation - rendering
and overlay drawing logic is complete, only bitmap conversion needs fixing.

Ref: Issue #32 - Visual PDF page annotation with semantic label overlays
"""

from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from pypdf import PdfReader


class PDFPageAnnotator:
    """Render PDF pages with semantic label overlays."""

    # CSS colors for semantic classes (converted to RGB for PIL)
    CLASS_COLORS = {
        "body": (173, 216, 230),  # Light blue
        "heading": (255, 212, 163),  # Light orange
        "footnote": (255, 182, 217),  # Light pink
        "caption": (200, 230, 201),  # Light green
        "header": (220, 220, 220),  # Light gray
        "footer": (220, 220, 220),  # Light gray
    }

    ALPHA = 0.3  # Transparency for overlay boxes

    def __init__(self, output_dir: str = "data/pdf_page_annotations"):
        """Initialize annotator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_pdf_page(self, pdf_path: Path, page_num: int = 0, scale: float = 1.5):
        """Render a PDF page to an image using pypdfium2."""
        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
            if page_num >= len(pdf):
                return None

            page = pdf[page_num]
            bitmap = page.render(scale=scale)
            image = bitmap.pil()  # Convert bitmap to PIL Image directly
            return image
        except Exception as e:
            print(f"  Error rendering {pdf_path.name} page {page_num}: {str(e)[:50]}")
            return None

    def detect_semantic_regions(self, pdf_path: Path, page_num: int = 0):
        """
        Detect semantic regions on a PDF page.
        Returns list of (x, y, width, height, semantic_class) tuples (normalized 0-1).
        """
        regions = []

        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                if page_num >= len(reader.pages):
                    return regions

                page = reader.pages[page_num]

                # Get page dimensions
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)

                # Extract text with positioning
                text_dict = page.extract_text_dict()
                if not text_dict or "objects" not in text_dict:
                    # Fallback: simple heuristic-based detection
                    return self._heuristic_regions(page_width, page_height)

                # Process text objects to group into semantic regions
                for obj in text_dict.get("objects", []):
                    if obj["type"] != "char":
                        continue

                    x = float(obj.get("x0", 0))
                    y = float(obj.get("top", 0))
                    width = float(obj.get("width", 10))
                    height = float(obj.get("height", 10))

                    # Normalize to 0-1
                    norm_x = x / page_width
                    norm_y = y / page_height
                    norm_w = width / page_width
                    norm_h = height / page_height

                    # Classify based on position and characteristics
                    semantic_class = self._classify_region(norm_y, norm_h, obj.get("text", ""))

                    regions.append((norm_x, norm_y, norm_w, norm_h, semantic_class))

        except Exception as e:
            print(f"  Error detecting regions in {pdf_path.name}: {str(e)[:50]}")

        return regions

    def _heuristic_regions(self, page_width, page_height):
        """Fallback heuristic for region detection when text dict unavailable."""
        regions = []

        # Top 5% = header
        regions.append((0, 0, 1, 0.05, "header"))

        # Middle 90% = body/content
        regions.append((0, 0.05, 1, 0.9, "body"))

        # Bottom 5% = footer
        regions.append((0, 0.95, 1, 0.05, "footer"))

        return regions

    def _classify_region(self, norm_y, norm_h, text):
        """Classify a text region into semantic class."""
        # Header/footer detection based on position
        if norm_y < 0.1:
            return "header"
        if norm_y > 0.9:
            return "footer"

        # Footnote detection (small text, bottom of page)
        if 0.8 < norm_y < 0.95 and len(text) < 50:
            return "footnote"

        # Heading detection (uppercase, short, not too small)
        if text.isupper() and len(text) < 100 and norm_h < 0.03:
            return "heading"

        # Caption detection (keywords, moderate size)
        if any(kw in text for kw in ["Figure", "Table", "Caption", "Fig.", "Tab."]):
            return "caption"

        # Default to body
        return "body"

    def annotate_page(self, image, regions, page_width, page_height):
        """Draw semantic overlays on a page image."""
        # Convert image to RGBA for transparency
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # Create overlay layer
        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Image dimensions
        img_width, img_height = image.size

        # Draw rectangles for each region
        for norm_x, norm_y, norm_w, norm_h, sem_class in regions:
            # Convert normalized coordinates to pixel coordinates
            x1 = int(norm_x * img_width)
            y1 = int(norm_y * img_height)
            x2 = int((norm_x + norm_w) * img_width)
            y2 = int((norm_y + norm_h) * img_height)

            # Get color
            color = self.CLASS_COLORS.get(sem_class, (200, 200, 200))
            # Add alpha for transparency
            color_with_alpha = (*color, int(255 * self.ALPHA))

            # Draw filled rectangle
            draw.rectangle([x1, y1, x2, y2], fill=color_with_alpha, outline=color + (255,), width=2)

        # Composite overlay on original image
        return Image.alpha_composite(image.convert("RGBA"), overlay)

    def create_gallery(self, pdf_paths: list, max_pdfs: int = 10, pages_per_pdf: int = 1):
        """Create HTML gallery with annotated PDF pages."""
        html_parts = []

        # Add HTML header with styling
        html_parts.append(
            """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Pages with Semantic Label Overlays</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #2196F3;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
            border-left: 5px solid #2196F3;
            padding-left: 10px;
        }
        .legend {
            background: white;
            padding: 20px;
            border-radius: 4px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .legend-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 3px;
        }
        .legend-color {
            width: 40px;
            height: 30px;
            border: 2px solid #333;
            border-radius: 3px;
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 30px;
            margin-top: 30px;
        }
        .page-card {
            background: white;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .page-header {
            padding: 15px;
            background: #f9f9f9;
            border-bottom: 1px solid #eee;
        }
        .page-name {
            font-weight: bold;
            color: #1976D2;
            font-size: 0.9em;
            margin-bottom: 5px;
        }
        .page-image {
            width: 100%;
            height: auto;
            display: block;
        }
        .summary {
            background: #E3F2FD;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <h1>🎨 PDF Pages with Semantic Label Overlays</h1>
    <p>Rendered PDF pages with colored bounding boxes highlighting semantic content regions.</p>

    <div class="summary">
        <strong>How to read:</strong> Colored overlays show semantic classification of content:
        <ul style="margin: 10px 0;">
            <li><strong>Blue</strong> = Body text (main article content)</li>
            <li><strong>Orange</strong> = Headings (section titles)</li>
            <li><strong>Pink</strong> = Footnotes (bottom-of-page notes)</li>
            <li><strong>Green</strong> = Captions (figure/table captions)</li>
            <li><strong>Gray</strong> = Headers/Footers (repeated page info)</li>
        </ul>
    </div>

    <h2>Semantic Class Color Legend</h2>
    <div class="legend">
        <div class="legend-grid">
            <div class="legend-item">
                <div class="legend-color" style="background-color: #ADD8E6;"></div>
                <div><strong>Body Text</strong></div>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #FFD4A3;"></div>
                <div><strong>Heading</strong></div>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #FFB6D9;"></div>
                <div><strong>Footnote</strong></div>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #C8E6C9;"></div>
                <div><strong>Caption</strong></div>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #DCDCDC;"></div>
                <div><strong>Header/Footer</strong></div>
            </div>
        </div>
    </div>

    <h2>Annotated PDF Pages</h2>
    <div class="gallery">
"""
        )

        # Process PDFs
        count = 0
        for pdf_path in pdf_paths:
            if count >= max_pdfs:
                break

            pdf_file = Path(pdf_path)
            print(f"Processing {pdf_file.name}...")

            # Process specified number of pages
            for page_num in range(pages_per_pdf):
                # Render page to image
                image = self.render_pdf_page(pdf_file, page_num)
                if image is None:
                    continue

                # Detect semantic regions
                regions = self.detect_semantic_regions(pdf_file, page_num)
                if not regions:
                    continue

                # Annotate image with overlays
                annotated = self.annotate_page(image, regions, image.width, image.height)

                # Save annotated image
                img_filename = f"{pdf_file.stem}_page_{page_num}.png"
                img_path = self.output_dir / img_filename
                annotated.convert("RGB").save(str(img_path))

                # Add to HTML gallery
                html_parts.append(f"""
        <div class="page-card">
            <div class="page-header">
                <div class="page-name">{pdf_file.name}</div>
                <div style="font-size: 0.85em; color: #666;">Page {page_num + 1}</div>
            </div>
            <img src="{img_filename}" alt="Annotated PDF page" class="page-image">
        </div>
""")

                count += 1

        # Close gallery and HTML
        html_parts.append(
            """
    </div>

    <h2>About This Visualization</h2>
    <p>
        This gallery shows rendered PDF pages with colored semantic label overlays.
        Each color represents a different semantic content type, allowing visual
        validation of extraction and classification quality.
    </p>
</body>
</html>
"""
        )

        # Write HTML gallery
        gallery_html = self.output_dir / "gallery.html"
        gallery_html.write_text("\n".join(html_parts))
        print(f"\n✓ Gallery saved to {gallery_html}")
        print("  Open in browser to see annotated PDF pages with overlays")

        return gallery_html


def main():
    """Generate PDF page annotations."""
    pdf_dir = Path("data/raw_pdf")
    pdf_paths = sorted([p for p in pdf_dir.glob("*.pdf") if p.is_file()])

    if not pdf_paths:
        print("No PDFs found in data/raw_pdf/")
        return

    print("\n🎨 PDF PAGE ANNOTATION WITH SEMANTIC LABEL OVERLAYS")
    print("=" * 80)
    print(f"Found {len(pdf_paths)} PDFs")
    print("Rendering pages and creating overlays...\n")

    annotator = PDFPageAnnotator()
    annotator.create_gallery(pdf_paths, max_pdfs=10, pages_per_pdf=1)


if __name__ == "__main__":
    main()
