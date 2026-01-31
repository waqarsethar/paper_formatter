"""Title page formatter: applies formatting to title, abstract, and keywords."""

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


def _find_abstract_paragraph(doc):
    """Return the paragraph that contains the abstract heading.

    Looks for a paragraph whose text starts with "abstract" (case-insensitive)
    or whose style name contains "abstract".
    """
    for paragraph in doc.paragraphs:
        style_name = (paragraph.style.name or "").lower()
        text = paragraph.text.strip().lower()
        if text.startswith("abstract") or "abstract" in style_name:
            return paragraph
    return None


def _find_keywords_paragraph(doc):
    """Return the paragraph that contains the keywords line.

    Looks for a paragraph whose text starts with "keyword" (case-insensitive).
    """
    for paragraph in doc.paragraphs:
        if paragraph.text.strip().lower().startswith("keyword"):
            return paragraph
    return None


def _count_abstract_body_words(doc, abstract_para) -> int:
    """Count the words in the abstract body.

    The abstract body is assumed to be the paragraphs between the abstract
    heading and the next headed paragraph (or keywords paragraph).  If the
    abstract heading and body are in the same paragraph (after a colon or
    similar), the body portion of that paragraph is counted instead.
    """
    # Check if abstract text contains body after heading on the same line.
    text = abstract_para.text.strip()
    # Strip the heading portion (e.g. "Abstract" or "ABSTRACT:")
    heading_match = re.match(r"^abstract\s*[:.]?\s*", text, re.IGNORECASE)
    if heading_match:
        remainder = text[heading_match.end():]
        if remainder.strip():
            return len(remainder.split())

    # Otherwise count words in subsequent paragraphs until a heading or
    # keyword line is reached.
    paragraphs = doc.paragraphs
    start_counting = False
    word_count = 0
    for para in paragraphs:
        if para is abstract_para:
            start_counting = True
            continue
        if not start_counting:
            continue

        # Stop at next heading or keywords.
        if para.style.name.startswith("Heading"):
            break
        if para.text.strip().lower().startswith("keyword"):
            break

        word_count += len(para.text.split())

    return word_count


def apply_title_page(doc, config) -> dict:
    """Apply title page, abstract, and keywords formatting.

    Reads ``config["title_page"]`` with keys:
        title: dict with font_size, bold, alignment, all_caps
        authors: dict with font_size, bold, alignment
        affiliation: dict with font_size, italic, alignment

    Reads ``config["abstract"]`` with keys:
        heading_text: str (e.g. ``"Abstract"`` or ``"ABSTRACT"``)
        font_size: float in pt
        max_words: int

    Reads ``config["keywords"]`` with keys:
        heading_text: str (e.g. ``"Keywords:"`` or ``"Key words:"``)
        separator: str (e.g. ``", "`` or ``"; "``)

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

    # ------------------------------------------------------------------
    # Abstract
    # ------------------------------------------------------------------
    abstract_config = config.get("abstract", {})
    abstract_para = _find_abstract_paragraph(doc)

    if abstract_para is not None:
        heading_text = abstract_config.get("heading_text", "Abstract")
        abstract_font_size = abstract_config.get("font_size")
        max_words = abstract_config.get("max_words")

        # Reformat abstract heading text.
        current_text = abstract_para.text
        new_text = re.sub(
            r"^abstract\s*[:.]?\s*",
            heading_text + " ",
            current_text,
            count=1,
            flags=re.IGNORECASE,
        ).rstrip()
        # If the replacement ended up only being the heading with trailing
        # space but no body, strip it.
        if new_text.strip() == heading_text:
            new_text = heading_text

        if abstract_para.runs:
            abstract_para.runs[0].text = new_text
            for run in abstract_para.runs[1:]:
                run.text = ""
        else:
            abstract_para.text = new_text

        # Apply font size to the abstract heading paragraph.
        if abstract_font_size is not None:
            for run in abstract_para.runs:
                run.font.size = Pt(abstract_font_size)

        # Word count check.
        if max_words is not None:
            word_count = _count_abstract_body_words(doc, abstract_para)
            if word_count > max_words:
                warnings.append(
                    f"Abstract contains approximately {word_count} words, "
                    f"which exceeds the maximum of {max_words}."
                )
    else:
        warnings.append("Could not identify an abstract section in the document.")

    # ------------------------------------------------------------------
    # Keywords
    # ------------------------------------------------------------------
    keywords_config = config.get("keywords", {})
    keywords_para = _find_keywords_paragraph(doc)

    if keywords_para is not None:
        heading_text = keywords_config.get("heading_text", "Keywords:")
        separator = keywords_config.get("separator", ", ")

        text = keywords_para.text
        # Split into heading part and keywords part.
        kw_match = re.match(
            r"^(keywords?\s*[:.]?\s*)(.*)",
            text,
            re.IGNORECASE,
        )
        if kw_match:
            _heading_part = kw_match.group(1)
            keywords_body = kw_match.group(2)

            # Detect the current separator by trying common options.
            current_sep = None
            for candidate in ("; ", ", ", ";", ","):
                if candidate in keywords_body:
                    current_sep = candidate
                    break

            if current_sep is not None and current_sep != separator:
                keywords_body = separator.join(
                    kw.strip() for kw in keywords_body.split(current_sep)
                )

            new_text = heading_text + " " + keywords_body

            if keywords_para.runs:
                keywords_para.runs[0].text = new_text
                for run in keywords_para.runs[1:]:
                    run.text = ""
            else:
                keywords_para.text = new_text

    return {"warnings": warnings, "stats": {}}
