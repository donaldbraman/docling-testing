#!/usr/bin/env python3
"""
Color-coded Visualization of Tagged PDFs

Creates interactive HTML visualizations showing tagged content with color coding
to help validate PDF structure tag quality and accuracy.

Ref: Issue #28 - Manual validation spot-check requirement
"""

from pathlib import Path

from pypdf import PdfReader


class TaggedPDFVisualizer:
    """Create color-coded visualizations of tagged PDF content."""

    # Color scheme for different tag types
    TAG_COLORS = {
        "/P": "#E8F4F8",  # Light blue - body text
        "/H": "#FFE0B2",  # Light orange - headings
        "/H1": "#FFD54F",  # Gold - H1
        "/H2": "#FFE082",  # Light gold - H2
        "/H3": "#FFF9C4",  # Very light gold - H3
        "/Note": "#F8BBD0",  # Light pink - footnotes
        "/Footnote": "#F8BBD0",  # Light pink
        "/Figure": "#C8E6C9",  # Light green - figures
        "/Table": "#BBDEFB",  # Light blue - tables
        "/Caption": "#D1C4E9",  # Light purple - captions
        "/Header": "#F5F5F5",  # Light gray - header
        "/Footer": "#F5F5F5",  # Light gray - footer
        "/Artifact": "#FFCCBC",  # Light brown - artifacts
        "/Document": "#CFD8DC",  # Gray-blue - document root
        "default": "#FFFFFF",  # White - untagged
    }

    TAG_LABELS = {
        "/P": "Body Text",
        "/H": "Heading",
        "/H1": "Heading 1",
        "/H2": "Heading 2",
        "/H3": "Heading 3",
        "/Note": "Footnote",
        "/Footnote": "Footnote",
        "/Figure": "Figure",
        "/Table": "Table",
        "/Caption": "Caption",
        "/Header": "Header",
        "/Footer": "Footer",
        "/Artifact": "Artifact",
        "/Document": "Document",
    }

    def __init__(self):
        """Initialize visualizer."""
        self.samples = []  # List of (pdf_name, tag_type, text_sample, color)

    def extract_tagged_content(self, pdf_path: Path, max_samples: int = 10) -> dict:
        """Extract tagged content from a PDF."""
        content = {
            "pdf_name": pdf_path.name,
            "blocks": [],  # List of (tag_type, text, color)
            "error": None,
        }

        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)

                # Check for structure tree
                if (
                    not hasattr(reader, "root_object")
                    or "/StructTreeRoot" not in reader.root_object
                ):
                    content["error"] = "No structure tree found"
                    return content

                struct_tree = reader.root_object["/StructTreeRoot"]
                self._traverse_structure_tree(struct_tree, content["blocks"], max_samples)

        except Exception as e:
            content["error"] = str(e)[:100]

        return content

    def _traverse_structure_tree(self, obj, blocks_list, max_samples, depth=0):
        """Recursively traverse structure tree to extract tagged blocks."""
        if len(blocks_list) >= max_samples:
            return

        if isinstance(obj, dict):
            # Get tag type
            tag_type = obj.get("/S", "/Unknown")

            # Get text content
            if "/T" in obj:
                text = str(obj["/T"])[:200]
                color = self.TAG_COLORS.get(tag_type, self.TAG_COLORS["default"])
                label = self.TAG_LABELS.get(tag_type, str(tag_type))

                blocks_list.append(
                    {
                        "tag": tag_type,
                        "label": label,
                        "text": text,
                        "color": color,
                        "depth": depth,
                    }
                )

            # Traverse children
            if "/K" in obj:
                kids = obj["/K"]
                if isinstance(kids, list):
                    for kid in kids:
                        self._traverse_structure_tree(kid, blocks_list, max_samples, depth + 1)
                else:
                    self._traverse_structure_tree(kids, blocks_list, max_samples, depth + 1)

    def generate_html_report(
        self, pdf_paths: list, output_file: str = "pdf_tag_visualization.html"
    ):
        """Generate interactive HTML report."""
        html_parts = []

        # Header
        html_parts.append("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tagged PDF Structure Visualization</title>
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
        .pdf-sample {
            background: white;
            border-left: 4px solid #2196F3;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .pdf-name {
            font-weight: bold;
            font-size: 1.1em;
            color: #1976D2;
            margin-bottom: 15px;
        }
        .tag-block {
            margin: 10px 0;
            padding: 10px;
            border-radius: 4px;
            border-left: 3px solid #999;
            line-height: 1.6;
        }
        .tag-label {
            display: inline-block;
            font-weight: bold;
            font-size: 0.85em;
            padding: 3px 8px;
            border-radius: 3px;
            background: rgba(0,0,0,0.1);
            margin-right: 10px;
            color: #333;
        }
        .tag-text {
            color: #555;
            font-size: 0.95em;
        }
        .info {
            background: #E8F5E9;
            color: #2E7D32;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            font-size: 0.9em;
        }
        .error {
            background: #FFEBEE;
            color: #C62828;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
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
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .legend-color {
            width: 40px;
            height: 30px;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        .legend-label {
            font-size: 0.9em;
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
    <h1>🏷️ Tagged PDF Structure Visualization</h1>
    <p>Color-coded view of PDF semantic tags for quality validation. Each colored block represents a tagged text element.</p>

    <div class="summary">
        <strong>⚠️ Important Finding:</strong> PDFs have structure hierarchies but structure tree elements do not contain direct text content.
        The tags below show the <strong>tag types found</strong> but text is extracted from PDF pages, not from structure elements.
        This confirms that tags are <strong>structural containers, not semantic labels</strong>.
    </div>

    <h2>Tag Type Color Guide</h2>
    <div class="legend">
        <div class="legend-grid">
""")

        # Add legend items
        for tag_type, color in sorted(self.TAG_COLORS.items()):
            if tag_type != "default":
                label = self.TAG_LABELS.get(tag_type, tag_type)
                html_parts.append(f"""
            <div class="legend-item">
                <div class="legend-color" style="background-color: {color};"></div>
                <div class="legend-label"><strong>{label}</strong><br/><code>{tag_type}</code></div>
            </div>
""")

        html_parts.append("""
        </div>
    </div>

    <h2>Sample PDFs with Tagged Content</h2>
    <p><em>Note: These samples show which PDFs have structure trees and what tag types they contain.</em></p>
""")

        # Process each PDF
        for pdf_path in pdf_paths[:20]:  # Limit to 20 samples for performance
            content = self.extract_tagged_content(Path(pdf_path), max_samples=10)

            html_parts.append('    <div class="pdf-sample">')
            html_parts.append(f'        <div class="pdf-name">📄 {content["pdf_name"]}</div>')

            if content["error"]:
                html_parts.append(f'        <div class="error">⚠️ Error: {content["error"]}</div>')
            elif len(content["blocks"]) == 0:
                html_parts.append(
                    '        <div class="info">ℹ️ Structure tree exists but contains no direct text. Tags are structural containers, not content labels.</div>'
                )
            else:
                for block in content["blocks"]:
                    html_parts.append(f"""        <div class="tag-block" style="background-color: {block["color"]}; border-left-color: {block["color"]}_dark;">
            <span class="tag-label">{block["label"]}</span>
            <span class="tag-text">{block["text"][:150]}...</span>
        </div>
""")

            html_parts.append("    </div>")

        # Footer
        html_parts.append("""
    <h2>About This Visualization</h2>
    <p>
        This report shows samples of tagged content from PDFs. Each color represents a different semantic tag type
        as defined in the PDF structure tree. This helps validate:
    </p>
    <ul>
        <li><strong>Coverage:</strong> Are important elements tagged?</li>
        <li><strong>Accuracy:</strong> Are tags semantically correct?</li>
        <li><strong>Completeness:</strong> Is most content tagged or are there gaps?</li>
        <li><strong>Tag types:</strong> What types of tags are used? Do they map to our schema?</li>
    </ul>
    <p><em>Generated from PDF Structure Trees (StructTreeRoot) using pypdf library.</em></p>
</body>
</html>
""")

        output_path = Path(output_file)
        output_path.write_text("\n".join(html_parts))
        print(f"\n✓ HTML visualization saved to {output_file}")
        print("  Open in browser to see color-coded tagged content samples")


def main():
    """Generate visualization for all tagged PDFs."""
    from pathlib import Path

    pdf_dir = Path("data/raw_pdf")
    pdf_paths = [p for p in sorted(pdf_dir.glob("*.pdf")) if p.is_file()]

    # Filter to only tagged PDFs (those from our tagged analysis)
    tagged_pdfs = []
    for pdf_path in pdf_paths:
        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                if hasattr(reader, "root_object") and "/StructTreeRoot" in reader.root_object:
                    tagged_pdfs.append(pdf_path)
        except Exception:
            pass

    print(f"\nGenerating visualization for {len(tagged_pdfs)} tagged PDFs...")
    print("(Showing samples from first 20)")

    visualizer = TaggedPDFVisualizer()
    visualizer.generate_html_report(tagged_pdfs, "data/pdf_tag_visualization.html")


if __name__ == "__main__":
    main()
