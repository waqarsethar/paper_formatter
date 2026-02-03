"""Footnotes formatter: validates and reports on footnotes (read-only).

NOTE: python-docx cannot create, modify, or renumber footnotes.
This formatter detects footnotes via XML and generates informational warnings.
"""

from __future__ import annotations


def _detect_footnote_references(doc) -> list[dict]:
    """Scan document XML for footnote reference elements.

    Looks for w:footnoteReference elements in paragraph runs.
    Uses XML iteration with element.tag.endswith('}footnoteReference').

    Returns list of footnote metadata (id, para_idx).
    """
    footnotes = []

    for para_idx, paragraph in enumerate(doc.paragraphs):
        for run in paragraph.runs:
            # Check for footnote reference elements in the run's XML
            for element in run._element.iter():
                tag = element.tag
                # Look for footnoteReference elements
                if tag.endswith('}footnoteReference'):
                    footnote_id = element.get(
                        '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id',
                        'unknown'
                    )
                    footnotes.append({
                        "id": footnote_id,
                        "para_idx": para_idx,
                    })

    return footnotes


def apply_footnotes(doc, config) -> dict:
    """Validate and report on footnotes (read-only).

    NOTE: python-docx cannot create, modify, or renumber footnotes.
    This formatter detects footnotes via XML and generates informational warnings.

    Reads ``config["footnotes"]`` with keys:
        numbering_format: "arabic" | "roman" | "symbols"
        restart_each_section: bool
        font_size: float (pt)
        max_per_page: int (validation only)
        position: "bottom_of_page" (informational)
        separator_line: bool (informational)

    Args:
        doc: A python-docx ``Document`` object.
        config: Journal configuration dict.

    Returns:
        dict with ``"warnings"`` (list[str]) and ``"stats"`` (dict).
    """
    warnings: list[str] = []

    footnotes_config = config.get("footnotes")
    if not footnotes_config:
        return {"warnings": warnings, "stats": {"footnotes_found": 0}}

    # Get configuration options
    numbering_format = footnotes_config.get("numbering_format", "arabic")
    max_per_page = footnotes_config.get("max_per_page")

    # Detect footnotes
    footnotes = _detect_footnote_references(doc)
    footnotes_found = len(footnotes)

    if footnotes_found > 0:
        warnings.append(
            f"Found {footnotes_found} footnote(s) in document. "
            "Note: python-docx cannot modify footnotes; "
            "manual formatting in Word may be required."
        )

        # Warn about numbering format if not arabic
        if numbering_format != "arabic":
            warnings.append(
                f"Footnote numbering format is set to '{numbering_format}', but "
                "automatic renumbering is not supported by python-docx. "
                "Please verify footnote numbering manually in Word."
            )

        # Warn about max per page if exceeded
        if max_per_page is not None and footnotes_found > max_per_page:
            warnings.append(
                f"Document contains {footnotes_found} footnotes, which may exceed "
                f"the recommended maximum of {max_per_page} per page. "
                "Please verify footnote distribution manually."
            )

    return {"warnings": warnings, "stats": {"footnotes_found": footnotes_found}}
