"""Heading formatter: applies font, spacing, alignment, color, and optional numbering to headings."""

from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


ALIGNMENT_MAP = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
}

HEADING_LEVELS = {
    "Heading 1": "heading_1",
    "Heading 2": "heading_2",
    "Heading 3": "heading_3",
}


def _parse_hex_color(hex_string):
    """Convert a hex color string like '#FF0000' to an RGBColor."""
    hex_string = hex_string.lstrip("#")
    r = int(hex_string[0:2], 16)
    g = int(hex_string[2:4], 16)
    b = int(hex_string[4:6], 16)
    return RGBColor(r, g, b)


def apply_headings(doc, config):
    """Apply heading-level formatting to Heading 1, 2, and 3 paragraphs.

    Reads config["fonts"] for heading_1, heading_2, heading_3 — each with:
        family: str
        size: float (pt)
        bold: bool
        italic: bool
        color: str (hex like "#000000")
        spacing_before: float (pt)
        spacing_after: float (pt)
        alignment: "left" or "center"

    Optionally adds hierarchical numbering (1., 1.1, 1.1.1) when
    config["fonts"]["heading_numbering"] is True.

    Args:
        doc: A python-docx Document object.
        config: Journal configuration dict.

    Returns:
        dict with "warnings" (list[str]) and "stats" (dict).
    """
    warnings = []
    stats = {}

    fonts_config = config.get("fonts", {})
    heading_numbering = fonts_config.get("heading_numbering", False)

    # Counters for heading numbering: level 1, 2, 3
    counters = [0, 0, 0]
    headings_formatted = {"Heading 1": 0, "Heading 2": 0, "Heading 3": 0}

    for paragraph in doc.paragraphs:
        style_name = paragraph.style.name

        if style_name not in HEADING_LEVELS:
            continue

        config_key = HEADING_LEVELS[style_name]
        heading_config = fonts_config.get(config_key)

        if heading_config is None:
            warnings.append(
                f"No configuration found for '{config_key}', "
                f"skipping formatting for '{style_name}'."
            )
            continue

        # --- Heading numbering ---
        if heading_numbering:
            if style_name == "Heading 1":
                counters[0] += 1
                counters[1] = 0
                counters[2] = 0
                prefix = f"{counters[0]}. "
            elif style_name == "Heading 2":
                counters[1] += 1
                counters[2] = 0
                prefix = f"{counters[0]}.{counters[1]} "
            elif style_name == "Heading 3":
                counters[2] += 1
                prefix = f"{counters[0]}.{counters[1]}.{counters[2]} "
            else:
                prefix = ""

            # Prepend the number prefix to the first run's text, or insert a
            # new run if the paragraph has no runs.
            if paragraph.runs:
                paragraph.runs[0].text = prefix + paragraph.runs[0].text
            else:
                paragraph.text = prefix + paragraph.text

        # --- Font family, size, bold, italic on every run ---
        family = heading_config.get("family", "Times New Roman")
        size = Pt(heading_config.get("size", 14.0))
        bold = heading_config.get("bold", True)
        italic = heading_config.get("italic", False)
        color_hex = heading_config.get("color", "#000000")
        color = _parse_hex_color(color_hex)

        for run in paragraph.runs:
            run.font.name = family
            run.font.size = size
            run.font.bold = bold
            run.font.italic = italic
            run.font.color.rgb = color

        # --- Paragraph spacing ---
        spacing_before = heading_config.get("spacing_before", 12.0)
        spacing_after = heading_config.get("spacing_after", 6.0)
        paragraph.paragraph_format.space_before = Pt(spacing_before)
        paragraph.paragraph_format.space_after = Pt(spacing_after)

        # --- Alignment ---
        alignment_name = heading_config.get("alignment", "left").lower()
        alignment = ALIGNMENT_MAP.get(alignment_name)
        if alignment is not None:
            paragraph.paragraph_format.alignment = alignment
        else:
            warnings.append(
                f"Unknown alignment '{alignment_name}' for {style_name}, "
                "defaulting to left."
            )
            paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

        headings_formatted[style_name] += 1

    stats["headings_formatted"] = headings_formatted
    stats["heading_numbering"] = heading_numbering

    return {"warnings": warnings, "stats": stats}
