"""Title page formatter: applies formatting to title, authors, and affiliation.

NOTE: Abstract and keywords formatting are now handled by dedicated formatters
(app/formatters/abstract.py and app/formatters/keywords.py).
"""

from __future__ import annotations

import re

from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


ALIGNMENT_MAP = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
}


def _apply_alignment(paragraph, alignment_name: str) -> None:
    """Set *paragraph* alignment from a string like ``"center"`` or ``"left"``."""
    alignment = ALIGNMENT_MAP.get(alignment_name.lower())
    if alignment is not None:
        paragraph.paragraph_format.alignment = alignment


def _find_title_paragraph(doc):
    """Return the first non-empty paragraph, preferring one with style 'Title'.

    Falls back to the first paragraph that has any non-whitespace text.
    """
    first_nonempty = None
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            if paragraph.style.name == "Title":
                return paragraph
            if first_nonempty is None:
                first_nonempty = paragraph
    return first_nonempty


def apply_title_page(doc, config) -> dict:
    """Apply title page formatting (title, authors, affiliation).

    NOTE: Abstract and keywords formatting are now handled by dedicated
    formatters (abstract.py and keywords.py).

    Reads ``config["title_page"]`` with keys:
        title: dict with font_size, bold, alignment, all_caps
        authors: dict with font_size, bold, alignment
        affiliation: dict with font_size, italic, alignment

    Args:
        doc: A python-docx ``Document`` object.
        config: Journal configuration dict.

    Returns:
        dict with ``"warnings"`` (list[str]) and ``"stats"`` (dict).
    """
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # Title
    # ------------------------------------------------------------------
    title_config = config.get("title_page", {}).get("title", {})
    title_para = _find_title_paragraph(doc)

    if title_para is not None:
        font_size = title_config.get("font_size", 14.0)
        bold = title_config.get("bold", True)
        alignment = title_config.get("alignment", "center")
        all_caps = title_config.get("all_caps", False)

        if all_caps:
            if title_para.runs:
                for run in title_para.runs:
                    run.text = run.text.upper()
            else:
                title_para.text = title_para.text.upper()

        for run in title_para.runs:
            run.font.size = Pt(font_size)
            run.font.bold = bold

        _apply_alignment(title_para, alignment)
    else:
        warnings.append("Could not identify a title paragraph in the document.")

    # Abstract and keywords are now handled by dedicated formatters
    # (app/formatters/abstract.py and app/formatters/keywords.py)

    return {"warnings": warnings, "stats": {}}
