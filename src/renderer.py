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
    ) -> bool:
        """
        Render DOCX with replaced placeholders.

        Args:
            placeholder_dict: Dict mapping {{placeholder}} to replacement values
            output_path: Path for output DOCX file
            adjust_cover_title: If True, adjust font size for long titles on cover page

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

            # Process all XML and .rels files in the entire DOCX package
            xml_files = []
            for root_dir, dirs, files in os.walk(temp_dir):
                for f in files:
                    if f.endswith(".xml") or f.endswith(".rels"):
                        rel_path = os.path.relpath(os.path.join(root_dir, f), temp_dir)
                        xml_files.append(rel_path.replace("\\", "/"))

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
        """Replace placeholders in XML file content. Handles plain, split XML runs, shapes, and diagrams.
        Returns the number of replacements performed.
        """
        import re

        with open(xml_path, "r", encoding="utf-8") as f:
            content = f.read()

        replacement_count = 0

        # Pass 1: Direct literal replacement
        for placeholder, value in placeholder_dict.items():
            if placeholder in content:
                count = content.count(placeholder)
                content = content.replace(placeholder, value)
                replacement_count += count

        # Pass 2: Character-level split XML tag matching for every placeholder key
        tag_pattern = r"(?:<[^>]+>)*\s*"
        for placeholder, value in placeholder_dict.items():
            key = placeholder.strip("{}")
            if not key:
                continue

            char_regex_parts = ["\\{\\{\\s*"]
            for char in key:
                char_regex_parts.append(re.escape(char) + tag_pattern)
            char_regex_parts.append("\\}\\}")

            pattern_str = "".join(char_regex_parts)
            regex = re.compile(pattern_str, re.IGNORECASE | re.DOTALL)

            matches = list(regex.finditer(content))
            for match in matches:
                raw_match = match.group(0)
                if raw_match in content:
                    content = content.replace(raw_match, value)
                    replacement_count += 1

        # Pass 3: General split XML tag matching regex
        split_pattern = re.compile(r"\{\{(?:<[^>]+>|[^}])*?\}\}", re.DOTALL)
        for match in list(split_pattern.finditer(content)):
            raw = match.group(0)
            clean_key = "{{" + re.sub(r"<[^>]+>", "", raw).strip("{}").strip() + "}}"
            value = placeholder_dict.get(clean_key)
            if value:
                content = content.replace(raw, value)
                replacement_count += 1

        # Pass 4: Clean up any remaining unreplaced {{...}} placeholders
        leftover_pattern = re.compile(r"\{\{[^}]+\}\}")
        leftovers = leftover_pattern.findall(content)
        if leftovers:
            content = leftover_pattern.sub("", content)
            replacement_count += len(leftovers)

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
    ) -> bool:
        """Render DOCX from a flat dictionary of placeholder to value mappings."""
        return self.render(payload_dict, output_path, adjust_cover_title)


def render_report(
    template_path: str,
    placeholder_dict: Dict[str, str],
    output_path: str,
    adjust_cover_title: bool = False,
) -> bool:
    """Standalone function to render a DOCX report."""
    renderer = DOCXRenderer(template_path)
    return renderer.render(placeholder_dict, output_path, adjust_cover_title)


if __name__ == "__main__":
    template = "templates/master_template_v1.docx"
    if os.path.exists(template):
        print("Testing DOCX operations...")
        print("Template exists and is accessible")
    else:
        print(f"Template not found: {template}")
