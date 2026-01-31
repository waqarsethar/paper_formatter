"""Font formatter: applies body font family and size to non-heading paragraphs."""

from docx.shared import Pt


def apply_fonts(doc, config):
    """Apply body font settings to all non-heading paragraphs.

    Reads config["fonts"]["body"] with keys:
        family: str (e.g. "Times New Roman")
        size: float (in pt, e.g. 12.0)

    Preserves existing bold, italic, and underline state on each run.

    Args:
        doc: A python-docx Document object.
        config: Journal configuration dict.

    Returns:
        dict with "warnings" (list[str]) and "stats" (dict).
    """
    warnings = []
    stats = {}

    fonts_config = config.get("fonts", {})
    body_config = fonts_config.get("body", {})

    family = body_config.get("family", "Times New Roman")
    size = body_config.get("size", 12.0)
    size_pt = Pt(size)

    paragraphs_modified = 0
    runs_modified = 0

    for paragraph in doc.paragraphs:
        # Skip headings — their formatting is handled by apply_headings
        if paragraph.style.name.startswith("Heading"):
            continue

        paragraph_touched = False

        for run in paragraph.runs:
            # Preserve existing bold, italic, underline state
            existing_bold = run.bold
            existing_italic = run.italic
            existing_underline = run.underline

            # Apply body font settings
            run.font.name = family
            run.font.size = size_pt

            # Restore preserved formatting
            run.bold = existing_bold
            run.italic = existing_italic
            run.underline = existing_underline

            runs_modified += 1
            paragraph_touched = True

        if paragraph_touched:
            paragraphs_modified += 1

    stats["font_family"] = family
    stats["font_size_pt"] = size
    stats["paragraphs_modified"] = paragraphs_modified
    stats["runs_modified"] = runs_modified

    return {"warnings": warnings, "stats": stats}
