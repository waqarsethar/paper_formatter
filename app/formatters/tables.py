"""Table formatter: applies border styles and caption formatting to tables."""

from __future__ import annotations

import re

from lxml import etree
from docx.oxml.ns import qn


def _int_to_roman(num: int) -> str:
    """Convert an integer to an uppercase Roman numeral string."""
    result = []
    for value, numeral in (
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ):
        while num >= value:
            result.append(numeral)
            num -= value
    return "".join(result)


def _format_number(n: int, numbering_format: str) -> str:
    """Return *n* formatted as arabic or roman."""
    if numbering_format == "roman":
        return _int_to_roman(n)
    return str(n)


# ---------------------------------------------------------------------------
# Border helpers
# ---------------------------------------------------------------------------

_BORDER_SIDES = ("top", "left", "bottom", "right", "insideH", "insideV")


def _make_border_element(val: str, sz: int = 4, space: int = 0,
                         color: str = "000000") -> etree._Element:
    """Create a single border sub-element with the given attributes."""
    el = etree.SubElement(etree.Element("dummy"), qn("w:top"))  # tag overwritten
    el.set(qn("w:val"), val)
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:space"), str(space))
    el.set(qn("w:color"), color)
    return el


def _set_table_borders(table, border_style: str) -> None:
    """Apply *border_style* to *table* via XML manipulation.

    Supported styles:
        ``"all"``         -- single-line borders on every side and interior.
        ``"top_bottom"``  -- horizontal borders only (top, bottom, insideH).
        ``"none"``        -- remove all borders.
    """
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    if tbl_pr is None:
        tbl_pr = etree.SubElement(tbl, qn("w:tblPr"))

    # Remove existing tblBorders element if present.
    for existing in tbl_pr.findall(qn("w:tblBorders")):
        tbl_pr.remove(existing)

    borders_el = etree.SubElement(tbl_pr, qn("w:tblBorders"))

    if border_style == "all":
        for side in _BORDER_SIDES:
            child = etree.SubElement(borders_el, qn(f"w:{side}"))
            child.set(qn("w:val"), "single")
            child.set(qn("w:sz"), "4")
            child.set(qn("w:space"), "0")
            child.set(qn("w:color"), "000000")

    elif border_style == "top_bottom":
        for side in ("top", "bottom", "insideH"):
            child = etree.SubElement(borders_el, qn(f"w:{side}"))
            child.set(qn("w:val"), "single")
            child.set(qn("w:sz"), "4")
            child.set(qn("w:space"), "0")
            child.set(qn("w:color"), "000000")
        for side in ("left", "right", "insideV"):
            child = etree.SubElement(borders_el, qn(f"w:{side}"))
            child.set(qn("w:val"), "none")
            child.set(qn("w:sz"), "0")
            child.set(qn("w:space"), "0")
            child.set(qn("w:color"), "000000")

    elif border_style == "none":
        for side in _BORDER_SIDES:
            child = etree.SubElement(borders_el, qn(f"w:{side}"))
            child.set(qn("w:val"), "none")
            child.set(qn("w:sz"), "0")
            child.set(qn("w:space"), "0")
            child.set(qn("w:color"), "000000")


# ---------------------------------------------------------------------------
# Caption helpers
# ---------------------------------------------------------------------------

# Matches "Table 1", "TABLE IV", "table 12", etc.
_CAPTION_RE = re.compile(
    r"^(table)\s+(\d+|[IVXLCDM]+)",
    re.IGNORECASE,
)


def _find_caption_for_table(doc, table, paragraphs_index_map):
    """Return ``(paragraph, position)`` for the caption of *table*.

    *position* is ``"above"`` or ``"below"`` depending on where the caption
    paragraph sits relative to the table element in the document XML.

    Returns ``(None, None)`` if no caption is found.
    """
    body = doc.element.body
    tbl_element = table._tbl

    # Get the element just before and just after the table in the body.
    prev_element = tbl_element.getprevious()
    next_element = tbl_element.getnext()

    # Check above first.
    if prev_element is not None and prev_element in paragraphs_index_map:
        para = paragraphs_index_map[prev_element]
        if _CAPTION_RE.match(para.text.strip()):
            return para, "above"

    # Check below.
    if next_element is not None and next_element in paragraphs_index_map:
        para = paragraphs_index_map[next_element]
        if _CAPTION_RE.match(para.text.strip()):
            return para, "below"

    return None, None


def _reformat_caption_text(text: str, prefix: str, number: int,
                           numbering_format: str) -> str:
    """Replace the table label in *text* with the configured prefix and number.

    For example ``"Table 1: Results"`` with prefix ``"TABLE"`` and
    numbering_format ``"roman"`` becomes ``"TABLE I: Results"``.
    """
    formatted_num = _format_number(number, numbering_format)
    new_label = f"{prefix} {formatted_num}"
    return _CAPTION_RE.sub(new_label, text, count=1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_tables(doc, config) -> dict:
    """Apply table formatting to all tables in *doc*.

    Reads ``config["tables"]`` with keys:
        caption_position: ``"above"`` or ``"below"``
        prefix: str (e.g. ``"Table"`` or ``"TABLE"``)
        numbering_format: ``"arabic"`` or ``"roman"``
        border_style: ``"all"``, ``"top_bottom"``, or ``"none"``

    Args:
        doc: A python-docx ``Document`` object.
        config: Journal configuration dict.

    Returns:
        dict with ``"warnings"`` (list[str]) and ``"stats"`` (dict).
    """
    warnings: list[str] = []
    tables_config = config.get("tables", {})

    caption_position = tables_config.get("caption_position", "above")
    prefix = tables_config.get("prefix", "Table")
    numbering_format = tables_config.get("numbering_format", "arabic")
    border_style = tables_config.get("border_style", "all")

    tables = doc.tables

    # Build a map from paragraph XML element -> paragraph object for quick
    # lookup when searching for captions adjacent to tables.
    paragraphs_index_map = {para._element: para for para in doc.paragraphs}

    table_number = 0

    for table in tables:
        table_number += 1

        # --- Border style ---
        _set_table_borders(table, border_style)

        # --- Caption ---
        caption_para, current_position = _find_caption_for_table(
            doc, table, paragraphs_index_map
        )

        if caption_para is not None:
            # Reformat caption text in first run (or paragraph text).
            new_text = _reformat_caption_text(
                caption_para.text, prefix, table_number, numbering_format
            )
            if caption_para.runs:
                # Replace text across runs: put reformatted text in the first
                # run and clear subsequent runs that were part of the label.
                caption_para.runs[0].text = new_text[
                    : len(new_text) - len(caption_para.text) + len(caption_para.runs[0].text)
                ] if len(caption_para.runs) > 1 else new_text
                if len(caption_para.runs) == 1:
                    caption_para.runs[0].text = new_text
                else:
                    # Simpler approach: rebuild via full paragraph text.
                    caption_para.runs[0].text = new_text
                    for run in caption_para.runs[1:]:
                        run.text = ""
            else:
                caption_para.text = new_text

            # Warn if position doesn't match.
            if current_position != caption_position:
                warnings.append(
                    f"Table {table_number} caption is currently {current_position} "
                    f"the table but should be {caption_position}. "
                    "Automatic repositioning is not supported; please move it manually."
                )
        else:
            warnings.append(
                f"No caption found for table {table_number}."
            )

    return {
        "warnings": warnings,
        "stats": {"tables_found": len(tables)},
    }
