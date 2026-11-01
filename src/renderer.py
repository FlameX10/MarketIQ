"""
DOCX Renderer module for safe placeholder replacement.
Handles XML manipulation while preserving formatting, styles, charts, and tables.
"""

import zipfile
import os
import shutil
import tempfile
import re
from typing import Dict, List, Tuple, Optional
from xml.etree import ElementTree as ET


class DOCXRenderer:
    """
    Safely replaces placeholders in DOCX XML while preserving formatting.

    Handles:
    - Split runs (placeholders split across multiple XML runs)
    - Placeholders in headers/footers
    - Preserve all styles, charts, tables, drawings
    - Safe XML manipulation with proper escaping
    - Font size adjustment for long cover page titles
    """

    # Font size reduction for long titles (in half-points, so 44pt = 88)
    # If title > 20 chars, reduce font size by 15pt (30 half-points)
    TITLE_FONT_REDUCTION = 30  # 15pt = 30 half-points

    def __init__(self, template_path: str):
        """
        Initialize renderer with template DOCX.

        Args:
            template_path: Path to template DOCX file
        """
        self.template_path = template_path
        self.namespaces = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
            "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }

        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)

        ET.register_namespace(
            "wpc", "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
        )
        ET.register_namespace(
            "mc", "http://schemas.openxmlformats.org/markup-compatibility/2006"
        )
        ET.register_namespace(
            "w14", "http://schemas.microsoft.com/office/word/2010/wordml"
        )
        ET.register_namespace(
            "w15", "http://schemas.microsoft.com/office/word/2012/wordml"
        )
        ET.register_namespace(
            "wp14",
            "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing",
        )
        ET.register_namespace("w10", "urn:schemas-microsoft-com:office:word")
        ET.register_namespace("v", "urn:schemas-microsoft-com:vml")
        ET.register_namespace(
            "m", "http://schemas.openxmlformats.org/officeDocument/2006/math"
        )
        ET.register_namespace("o", "urn:schemas-microsoft-com:office:office")

    @staticmethod
    def escape_xml(text: str) -> str:
        """
        Escape special XML characters in text.
        Only escapes characters that would break XML parsing.
        """
        if not text:
            return text
        result = str(text)
        result = result.replace("&", "&amp;")
        result = result.replace("<", "&lt;")
        result = result.replace(">", "&gt;")
        return result

    def render(
        self,
        placeholder_dict: Dict[str, str],
        output_path: str,
        adjust_cover_title: bool = False,
        players: Optional[List[str]] = None,
    ) -> bool:
        """
        Render DOCX with replaced placeholders.

        Args:
            placeholder_dict: Dict mapping {{placeholder}} to replacement values
            output_path: Path for output DOCX file
            adjust_cover_title: If True, adjust font size for long titles on cover page
            players: Optional list of competitor/key player names for Section 12.1

        Returns:
            True if successful, False otherwise
        """
        temp_dir = tempfile.mkdtemp()

        try:
            self._extract_docx(self.template_path, temp_dir)

            escaped_dict = {}
            for placeholder, value in placeholder_dict.items():
                escaped_dict[placeholder] = self.escape_xml(value)

            # Legacy: replace old hardcoded BESS values in embedded .xlsx shared strings
            # with the correct tech_segment values so Word displays them properly.
            legacies = {
                "&lt; 500 kW": ("{{tech_segment_1}}", "tech_segment_1"),
                "500 kW \u2013 5 MW": ("{{tech_segment_2}}", "tech_segment_2"),
                "&gt; 5 MW (Utility/MW-scale)": (
                    "{{tech_segment_3}}",
                    "tech_segment_3",
                ),
            }
            for raw, (placeholder, key) in legacies.items():
                if placeholder in placeholder_dict:
                    escaped_dict[raw] = self.escape_xml(placeholder_dict[placeholder])
                elif key in placeholder_dict:
                    escaped_dict[raw] = self.escape_xml(placeholder_dict[key])

            xml_files = ["word/document.xml", "word/header1.xml", "word/footer1.xml"]

            # Also process all chart XML files
            charts_dir = os.path.join(temp_dir, "word", "charts")
            if os.path.isdir(charts_dir):
                for f in sorted(os.listdir(charts_dir)):
                    if f.endswith(".xml"):
                        xml_files.append(f"word/charts/{f}")

            total_replacements = 0
            for xml_file in xml_files:
                file_path = os.path.join(temp_dir, xml_file)
                if os.path.exists(file_path):
                    count = self._replace_in_xml(file_path, escaped_dict)
                    total_replacements += count

            # Process embedded Excel files for placeholder replacement
            # NOTE: .xls files are skipped because byte-level replacement
            # corrupts the BIFF binary structure (string length prefixes are
            # not updated), causing Word "unreadable content" recovery that
            # destroys chart colors and data. Chart XML cache + .xlsx data
            # is sufficient for correct rendering.
            embeddings_dir = os.path.join(temp_dir, "word", "embeddings")
            if os.path.isdir(embeddings_dir):
                for emb_file in sorted(os.listdir(embeddings_dir)):
                    file_path = os.path.join(embeddings_dir, emb_file)
                    if emb_file.lower().endswith(".xlsx"):
                        count = self._replace_in_xlsx(file_path, escaped_dict)
                        total_replacements += count

            print(f"  Total replacements: {total_replacements}")

            # Adjust cover page title font size if needed
            if adjust_cover_title:
                print("  Adjusting cover page title font size...")
                self._adjust_cover_title_font(temp_dir)

            # Inject competitor list below Section 12.1 chart
            if players:
                self._inject_competitor_list(temp_dir, players)

            self._pack_docx(temp_dir, output_path)

            print(f"Rendered DOCX saved to: {output_path}")
            return True

        except Exception as e:
            print(f"Error rendering DOCX: {e}")
            import traceback

            traceback.print_exc()
            return False

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _extract_docx(self, docx_path: str, extract_dir: str):
        """Extract DOCX contents to directory."""
        with zipfile.ZipFile(docx_path, "r") as zf:
            zf.extractall(extract_dir)

    def _pack_docx(self, source_dir: str, output_path: str):
        """Pack directory contents into DOCX."""
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zf.write(file_path, arcname)

    def _replace_in_xml(self, xml_path: str, placeholder_dict: Dict[str, str]) -> int:
        """Replace placeholders in XML file content. Handles both plain and split placeholders.
        Returns the number of replacements performed.
        """
        import re

        # Load XML content
        with open(xml_path, "r", encoding="utf-8") as f:
            content = f.read()

        replacement_count = 0

        # First pass: replace plain placeholders (no inner XML tags)
        for placeholder, value in placeholder_dict.items():
            if placeholder in content:
                count = content.count(placeholder)
                content = content.replace(placeholder, value)
                replacement_count += count

        # Second pass: handle split placeholders containing XML tags
        split_pattern = re.compile(r"\{\{(?:[^\}]*\u003c[^\u003e]+\u003e)+[^\}]*\}\}")
        for match in split_pattern.finditer(content):
            raw = match.group(0)
            # Strip XML tags to get the clean placeholder key (including braces)
            clean_key = re.sub(r"\u003c[^\u003e]+\u003e", "", raw)
            value = placeholder_dict.get(clean_key)
            if value:
                content = content.replace(raw, value)
                replacement_count += 1

        # Final cleanup: remove any remaining unreplaced placeholders
        leftover_pattern = re.compile(r"\{\{[^\}]+\}\}")
        leftovers = leftover_pattern.findall(content)
        if leftovers:
            # Replace them with empty string (or you could keep the placeholder for debugging)
            content = leftover_pattern.sub("", content)
            replacement_count += len(leftovers)

        # Write back modified XML
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(content)

        return replacement_count

    def _replace_in_xlsx(self, xlsx_path: str, placeholder_dict: Dict[str, str]) -> int:
        """Replace placeholders inside .xlsx (ZIP of XML) files.
        Unzips, processes all XML files for placeholder replacement, re-zips.
        """
        import io, tempfile

        with open(xlsx_path, "rb") as f:
            xlsx_data = f.read()

        temp_dir_xlsx = tempfile.mkdtemp()
        try:
            # Extract .xlsx contents
            with zipfile.ZipFile(io.BytesIO(xlsx_data)) as zf:
                zf.extractall(temp_dir_xlsx)

            # Process all XML files in the extracted .xlsx
            replacement_count = 0
            for root_dir, dirs, files in os.walk(temp_dir_xlsx):
                for file in files:
                    if file.endswith(".xml"):
                        xml_path = os.path.join(root_dir, file)
                        count = self._replace_in_xml(xml_path, placeholder_dict)
                        replacement_count += count

            # Re-pack into .xlsx
            output_buffer = io.BytesIO()
            with zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as zf_out:
                for root_dir, dirs, files in os.walk(temp_dir_xlsx):
                    for file in files:
                        file_path = os.path.join(root_dir, file)
                        arcname = os.path.relpath(file_path, temp_dir_xlsx)
                        zf_out.write(file_path, arcname)

            with open(xlsx_path, "wb") as f:
                f.write(output_buffer.getvalue())

            return replacement_count

        finally:
            shutil.rmtree(temp_dir_xlsx, ignore_errors=True)

    def _inject_competitor_list(self, extract_dir: str, players: List[str]):
        """
        Inject competitor names as a formatted text list into the document XML,
        directly after the Section 12.1 market share chart image (image25.png).

        This finds the <w:drawing> referencing rId32 (image25.png) and inserts
        styled Word XML paragraphs immediately after its parent <w:p>.
        """
        document_path = os.path.join(extract_dir, "word", "document.xml")
        if not os.path.exists(document_path):
            return

        with open(document_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find the paragraph that contains the market share chart image
        # The chart is referenced by rId32 -> media/image25.png
        chart_ref_pattern = re.compile(
            r"(<w:p\b[^>]*>(?:(?!</w:p>).)*?r:embed=\"rId32\"(?:(?!</w:p>).)*?</w:p>)",
            re.DOTALL,
        )
        match = chart_ref_pattern.search(content)

        if not match:
            # Fallback: search for the 'Market Share Analysis' heading paragraph
            # and insert after the next paragraph (which is the chart paragraph)
            fallback_pattern = re.compile(
                r"(Market Share Analysis(?:(?!</w:p>).)*?</w:p>)",
                re.DOTALL,
            )
            match = fallback_pattern.search(content)
            if not match:
                print("  Warning: Could not locate Section 12.1 chart position — competitor list not injected")
                return

        # Build the XML block to insert after the chart paragraph
        # Use a heading-style paragraph for the label, then one paragraph per company
        NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

        def make_company_paragraph(name: str, index: int) -> str:
            """Create a styled <w:p> paragraph for a single company name."""
            color = "1B3A6E" if index % 2 == 0 else "2B5BA8"
            escaped_name = self.escape_xml(name.upper())
            return (
                f'<w:p>'
                f'<w:pPr>'
                f'<w:pStyle w:val="Normal"/>'
                f'<w:ind w:left="360"/>'
                f'<w:spacing w:before="40" w:after="40"/>'
                f'</w:pPr>'
                f'<w:r>'
                f'<w:rPr>'
                f'<w:color w:val="{color}"/>'
                f'<w:sz w:val="18"/>'
                f'<w:szCs w:val="18"/>'
                f'</w:rPr>'
                f'<w:t xml:space="preserve">\u25a0  {escaped_name}</w:t>'
                f'</w:r>'
                f'</w:p>'
            )

        # Header paragraph
        header_para = (
            '<w:p>'
            '<w:pPr>'
            '<w:pStyle w:val="Normal"/>'
            '<w:spacing w:before="120" w:after="60"/>'
            '</w:pPr>'
            '<w:r>'
            '<w:rPr>'
            '<w:b/>'
            '<w:color w:val="1B3A6E"/>'
            '<w:sz w:val="20"/>'
            '<w:szCs w:val="20"/>'
            '</w:rPr>'
            '<w:t>KEY MARKET PLAYERS (2024)</w:t>'
            '</w:r>'
            '</w:p>'
        )

        company_paras = "".join(
            make_company_paragraph(name, i)
            for i, name in enumerate(players[:10])
        )

        injection = header_para + company_paras

        # Insert the block immediately after the chart paragraph
        insert_after = match.group(0)
        content = content.replace(insert_after, insert_after + injection, 1)

        with open(document_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  Injected competitor list ({len(players[:10])} companies) after Section 12.1 chart")

    def _adjust_cover_title_font(self, extract_dir: str):
        """
        Reduce font size in the cover page title area if title is long.
        This finds the {{market_name_title}} placeholder run and reduces font size.
        """
        document_path = os.path.join(extract_dir, "word", "document.xml")

        if not os.path.exists(document_path):
            return

        with open(document_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find the market_name_title placeholder and reduce font size in surrounding runs
        # The font size is in <w:sz w:val="XX"/> format (half-points)
        # Look for runs containing market_name_upper (used throughout) near the cover page area

        # Pattern to find font size declarations near market_name title
        # This regex looks for <w:sz w:val="XX"/> that appears near {{market_name_title}}
        pattern = r"(<w:r[^>]*>.*?\{\{market_name_title\}\}.*?</w:r>)"

        # Alternative approach: find and modify font size values in the document
        # Reduce all large font sizes (likely title fonts) by the reduction amount
        # This is a simplification - ideally we'd target only the cover page title

        # Find <w:sz w:val="XX"/> patterns and reduce by TITLE_FONT_REDUCTION
        # Only reduce if current size > 60 (30pt, which is a reasonable title size)

        def reduce_font_size(match):
            full_match = match.group(0)
            # Extract current font size
            size_match = re.search(r'<w:sz w:val="(\d+)"/>', full_match)
            if size_match:
                current_size = int(size_match.group(1))
                # Only reduce if size is large enough (title font)
                if current_size > 60:
                    new_size = max(30, current_size - self.TITLE_FONT_REDUCTION)
                    return full_match.replace(
                        f'<w:sz w:val="{current_size}"/>', f'<w:sz w:val="{new_size}"/>'
                    )
            return full_match

        # Find runs near market_name_upper (which is used in cover page)
        # Look for runs that contain the market name with large font
        content = re.sub(
            r"<w:r\b[^>]*>(?:(?!</w:r>).)*?\{\{market_name_upper\}\}(?:(?!</w:r>).)*?</w:r>",
            reduce_font_size,
            content,
            flags=re.DOTALL,
        )

        # Also adjust market_name_title runs
        content = re.sub(
            r"<w:r\b[^>]*>(?:(?!</w:r>).)*?\{\{market_name_title\}\}(?:(?!</w:r>).)*?</w:r>",
            reduce_font_size,
            content,
            flags=re.DOTALL,
        )

        with open(document_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  Cover title font size reduced by {self.TITLE_FONT_REDUCTION // 2}pt")

    def render_from_json(
        self,
        payload_dict: Dict[str, str],
        output_path: str,
        adjust_cover_title: bool = False,
        players: Optional[List[str]] = None,
    ) -> bool:
        """Render DOCX from a flat dictionary of placeholder to value mappings."""
        return self.render(payload_dict, output_path, adjust_cover_title, players)


def render_report(
    template_path: str,
    placeholder_dict: Dict[str, str],
    output_path: str,
    adjust_cover_title: bool = False,
    players: Optional[List[str]] = None,
) -> bool:
    """Standalone function to render a DOCX report."""
    renderer = DOCXRenderer(template_path)
    return renderer.render(placeholder_dict, output_path, adjust_cover_title, players)


if __name__ == "__main__":
    template = "templates/master_template_v1.docx"
    if os.path.exists(template):
        print("Testing DOCX operations...")
        print("Template exists and is accessible")
    else:
        print(f"Template not found: {template}")
