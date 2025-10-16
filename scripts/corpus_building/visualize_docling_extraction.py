#!/usr/bin/env python3
"""
Visual Quality Validation of Docling Semantic Extraction

Uses Docling's existing extraction + bounding boxes to create annotated PDF
page images with colored overlays showing semantic labels. Enables manual
validation of extraction quality for deciding if tagged PDFs can be used for
training.

Color coding:
- Body text (light blue #ADD8E6)
- Headings (light orange #FFD4A3)
- Footnotes (light pink #FFB6D9)
- Captions (light green #C8E6C9)
- Headers/Footers (light gray #DCDCDC)

Ref: Issue #33 - Visual quality validation of Docling extraction
"""

from pathlib import Path

import pypdfium2 as pdfium
from docling.document_converter import DocumentConverter
from PIL import Image, ImageDraw


class DoclingExtractionVisualizer:
    """Visualize Docling semantic extraction with colored overlays."""

    # RGB colors for semantic classes
    CLASS_COLORS = {
        "body": (173, 216, 230),  # Light blue
        "heading": (255, 212, 163),  # Light orange
        "footnote": (255, 182, 217),  # Light pink
        "caption": (200, 230, 201),  # Light green
        "header": (220, 220, 220),  # Light gray
        "footer": (220, 220, 220),  # Light gray
        "cover": (216, 200, 230),  # Light purple
    }

    OVERLAY_ALPHA = 0.4  # Transparency (0-1)

    def __init__(self, output_dir: str = "data/pdf_page_annotations"):
        """Initialize visualizer."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.converter = None  # Lazy initialization

    def render_pdf_page(self, pdf_path: Path, page_num: int = 0):
        """Render PDF page to image."""
        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
            if page_num >= len(pdf):
                return None, None, None

            page = pdf[page_num]
            width = page.get_width()
            height = page.get_height()

            # Render at 150 DPI (scale 1.5)
            bitmap = page.render(scale=1.5)
            # Convert bitmap to PIL Image
            image = Image.new("RGB", (bitmap.width, bitmap.height), "white")
            image.paste(
                Image.frombytes("RGB", (bitmap.width, bitmap.height), bitmap.buffer, "raw", "RGB")
            )

            return image, width, height
        except Exception as e:
            print(f"  Error rendering {pdf_path.name} page {page_num}: {str(e)[:50]}")
            return None, None, None

    def extract_blocks_with_boxes(self, pdf_path: Path, page_num: int = 0):
        """Extract blocks with bounding boxes from PDF using Docling."""
        try:
            if self.converter is None:
                self.converter = DocumentConverter()
            doc = self.converter.convert(str(pdf_path))

            blocks = []
            # Content is in doc.document.body.children
            if (
                hasattr(doc, "document")
                and hasattr(doc.document, "body")
                and hasattr(doc.document.body, "children")
            ):

                def traverse_items(items):
                    """Recursively traverse body children to find blocks with bbox."""
                    result = []
                    for item in items:
                        # Check if item has bbox and text
                        if hasattr(item, "bbox") and hasattr(item, "text"):
                            result.append(item)
                        # Recursively check children
                        if hasattr(item, "children") and item.children:
                            result.extend(traverse_items(item.children))
                    return result

                all_items = traverse_items(doc.document.body.children)

                for item in all_items:
                    if not hasattr(item, "bbox") or not hasattr(item, "text"):
                        continue

                    # Get semantic class from item type
                    item_type = item.__class__.__name__.lower()

                    if "heading" in item_type or "title" in item_type:
                        sem_class = "heading"
                    elif "footnote" in item_type or "note" in item_type:
                        sem_class = "footnote"
                    elif "caption" in item_type or "figure" in item_type or "table" in item_type:
                        sem_class = "caption"
                    elif "header" in item_type or "page_header" in item_type:
                        sem_class = "header"
                    elif "footer" in item_type or "page_footer" in item_type:
                        sem_class = "footer"
                    else:
                        sem_class = "body"

                    # Get bounding box (should be normalized 0-999)
                    bbox = item.bbox
                    if bbox:
                        text_content = item.text if hasattr(item, "text") else ""
                        blocks.append(
                            {
                                "text": str(text_content)[:100] if text_content else "",
                                "bbox": bbox,  # (x0, y0, x1, y1) in 0-999 range
                                "class": sem_class,
                            }
                        )

            return blocks

        except Exception as e:
            print(f"  Error extracting {pdf_path.name}: {str(e)[:100]}")
            import traceback

            traceback.print_exc()
            return []

    def draw_overlays(self, image, blocks, page_width, page_height):
        """Draw colored overlays on image for each block."""
        draw = ImageDraw.Draw(image, "RGBA")

        img_width, img_height = image.size

        for block in blocks:
            x0, y0, x1, y1 = block["bbox"]

            # Normalize from 0-999 range to pixel coordinates
            px0 = int((x0 / 999.0) * img_width)
            py0 = int((y0 / 999.0) * img_height)
            px1 = int((x1 / 999.0) * img_width)
            py1 = int((y1 / 999.0) * img_height)

            # Get color and add alpha
            color = self.CLASS_COLORS.get(block["class"], (200, 200, 200))
            color_with_alpha = (*color, int(255 * self.OVERLAY_ALPHA))

            # Draw filled rectangle
            draw.rectangle(
                [px0, py0, px1, py1], fill=color_with_alpha, outline=color + (255,), width=2
            )

        return image

    def create_gallery(self, pdf_paths: list, max_pdfs: int = 10):
        """Create HTML gallery with annotated pages."""
        html_parts = []

        # HTML header
        html_parts.append(
            """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Docling Extraction Quality Validation</title>
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
        }
        .legend-color {
            width: 50px;
            height: 30px;
            border: 2px solid #333;
            border-radius: 3px;
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(700px, 1fr));
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
            font-size: 0.95em;
            margin-bottom: 5px;
        }
        .page-stats {
            font-size: 0.85em;
            color: #666;
        }
        .page-image {
            width: 100%;
            height: auto;
            display: block;
            border-top: 1px solid #eee;
            border-bottom: 1px solid #eee;
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
    <h1>🎨 Docling Extraction Quality Validation</h1>
    <p>Docling's semantic extraction with colored bounding box overlays for manual validation.</p>

    <div class="summary">
        <strong>Validation Process:</strong> Review each annotated page to assess:
        <ul style="margin: 10px 0;">
            <li>Are semantic labels correct?</li>
            <li>Are bounding boxes accurately positioned?</li>
            <li>Is extraction quality acceptable for training?</li>
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

    <h2>Annotated Sample Pages</h2>
    <div class="gallery">
"""
        )

        # Process PDFs
        processed = 0
        for pdf_path in pdf_paths:
            if processed >= max_pdfs:
                break

            processed += 1
            pdf_file = Path(pdf_path)
            print(f"Processing {pdf_file.name}...")

            # Render page
            image, page_width, page_height = self.render_pdf_page(pdf_file, 0)
            if image is None:
                continue

            # Extract blocks with bounding boxes
            blocks = self.extract_blocks_with_boxes(pdf_file, 0)
            if not blocks:
                print("  No blocks extracted")
                continue

            # Draw overlays
            annotated = self.draw_overlays(image, blocks, page_width, page_height)

            # Save image
            img_filename = f"{pdf_file.stem}_page_0.png"
            img_path = self.output_dir / img_filename
            annotated.save(str(img_path))

            # Count blocks by class
            class_counts = {}
            for block in blocks:
                cls = block["class"]
                class_counts[cls] = class_counts.get(cls, 0) + 1

            # Add to gallery
            stats = " | ".join([f"{cls}: {cnt}" for cls, cnt in sorted(class_counts.items())])

            html_parts.append(f"""
        <div class="page-card">
            <div class="page-header">
                <div class="page-name">{pdf_file.name}</div>
                <div class="page-stats">{stats}</div>
            </div>
            <img src="{img_filename}" alt="Annotated page" class="page-image">
        </div>
""")

        # Close gallery
        html_parts.append(
            """
    </div>

    <h2>Notes</h2>
    <p>
        Each colored box represents a semantic block extracted by Docling.
        The overlay shows the bounding box and semantic classification.
        Use this to validate whether extraction quality is sufficient for training.
    </p>
</body>
</html>
"""
        )

        # Write HTML
        gallery_html = self.output_dir / "gallery.html"
        gallery_html.write_text("\n".join(html_parts))
        print(f"\n✓ Gallery saved to {gallery_html}")
        print(f"  Processed {processed} PDFs")

        return gallery_html


def main():
    """Generate Docling extraction visualizations."""
    pdf_dir = Path("data/raw_pdf")
    pdf_paths = sorted([p for p in pdf_dir.glob("*.pdf") if p.is_file()])

    if not pdf_paths:
        print("No PDFs found in data/raw_pdf/")
        return

    print("\n🎨 DOCLING EXTRACTION QUALITY VALIDATION")
    print("=" * 80)
    print(f"Found {len(pdf_paths)} PDFs")
    print("Rendering and annotating pages...\n")

    visualizer = DoclingExtractionVisualizer()
    visualizer.create_gallery(pdf_paths, max_pdfs=10)


if __name__ == "__main__":
    main()
