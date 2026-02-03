"""Layout formatter: applies page margins, page size, and line spacing."""

from docx.shared import Inches, Pt
from docx.enum.text import WD_LINE_SPACING


PAGE_SIZES = {
    "letter": (Inches(8.5), Inches(11)),
    "a4": (Inches(8.27), Inches(11.69)),
}


def apply_layout(doc, config):
    """Apply page layout settings to the document.

    Reads config["page_layout"] with keys:
        margins: dict with top, bottom, left, right (in inches)
        page_size: "letter" or "a4"
        line_spacing: float (1.0, 1.5, 2.0, etc.)
        columns: int (informational only)

    Args:
        doc: A python-docx Document object.
        config: Journal configuration dict.

    Returns:
        dict with "warnings" (list[str]) and "stats" (dict).
    """
    warnings = []
    stats = {}

    layout = config.get("page_layout", {})

    # --- Page size ---
    page_size_name = layout.get("page_size", "letter").lower()
    if page_size_name in PAGE_SIZES:
        width, height = PAGE_SIZES[page_size_name]
    else:
        warnings.append(
            f"Unknown page size '{page_size_name}', defaulting to letter."
        )
        width, height = PAGE_SIZES["letter"]

    for section in doc.sections:
        section.page_width = width
        section.page_height = height

    stats["page_size"] = page_size_name

    # --- Margins ---
    margins = layout.get("margins", {})
    margin_top = Inches(margins.get("top", 1.0))
    margin_bottom = Inches(margins.get("bottom", 1.0))
    margin_left = Inches(margins.get("left", 1.0))
    margin_right = Inches(margins.get("right", 1.0))

    for section in doc.sections:
        section.top_margin = margin_top
        section.bottom_margin = margin_bottom
        section.left_margin = margin_left
        section.right_margin = margin_right

    stats["margins"] = {
        "top": margins.get("top", 1.0),
        "bottom": margins.get("bottom", 1.0),
        "left": margins.get("left", 1.0),
        "right": margins.get("right", 1.0),
    }

    # --- Line spacing ---
    line_spacing_value = layout.get("line_spacing", 1.0)

    for paragraph in doc.paragraphs:
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        paragraph.paragraph_format.line_spacing = line_spacing_value

    stats["line_spacing"] = line_spacing_value

    # --- Columns (informational only) ---
    columns = layout.get("columns", 1)
    if columns > 1:
        warnings.append(
            f"Two-column layout ({columns} columns) requested. "
            "python-docx cannot apply multi-column formatting automatically. "
            "After downloading the formatted document:\n"
            "1. Open in Microsoft Word\n"
            "2. Select all content (Ctrl+A)\n"
            "3. Go to Layout → Columns → Two Columns\n"
            "4. Save the document"
        )
    stats["columns"] = columns

    return {"warnings": warnings, "stats": stats}
