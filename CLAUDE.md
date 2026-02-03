# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

A web application that reformats research paper manuscripts (.doc/.docx) to match specific journal formatting requirements. Authors upload their manuscript, select a target journal (IEEE, APA, Nature, Elsevier, Springer, PLOS ONE), and download a professionally reformatted document. The formatting pipeline handles page layout, fonts, headings, citations, references, tables, figures, title pages, abstracts, keywords, appendices, footnotes, and section ordering — all driven by per-journal JSON configuration files.

Built with **Python + FastAPI**, using **python-docx** for document manipulation, **Jinja2** for templating, and vanilla HTML/CSS/JS for the frontend.

## Build / Test Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start development server (with hot reload)
uvicorn main:app --reload

# Start production server
uvicorn main:app --host 0.0.0.0 --port 8000

# Open in browser
# http://localhost:8000
```

## Project Structure

- `main.py` — FastAPI app entry point
- `config.py` — Settings via pydantic-settings (reads `.env`)
- `app/api/` — Routes and Pydantic schemas
- `app/core/` — Pipeline orchestrator, doc converter, document parser utils
- `app/formatters/` — One module per formatting step (layout, fonts, headings, citations, references, tables, figures, sections, title_page, abstract, keywords, appendix, footnotes, equations)
- `app/services/` — File handling and email (email currently unused)
- `app/journal_configs/` — One JSON config per journal defining all style rules
- `app/templates/` — Jinja2 HTML templates
- `app/static/` — CSS and JS

## Architecture Overview

### Pipeline Execution Order

The formatting pipeline (`app/core/pipeline.py`) executes formatters in a specific order to avoid conflicts:

1. **layout** — Page margins, size, line spacing, column warnings
2. **fonts** — Body and heading font families, sizes, colors
3. **footnotes** — Detect and validate footnotes (read-only, python-docx limitation)
4. **title_page** — Format title, authors, affiliation
5. **abstract** — Format abstract heading and body, word count validation
6. **keywords** — Format keywords line with separators, italic styling
7. **sections** — Validate section ordering (reports mismatches only)
8. **citations** — Reformat in-text citations (numeric, author-year, superscript)
9. **references** — Reformat reference list entries
10. **headings** — Apply heading numbering (MUST run AFTER content detection)
11. **appendix** — Detect and label appendix sections (A, B, C or I, II, III)
12. **tables** — Format table captions and numbering
13. **figures** — Format figure captions and numbering
14. **equations** — Detect and number equations

**Critical ordering constraint**: Content-detecting steps (title_page, abstract, keywords, sections, citations, references, appendix) MUST run BEFORE the `headings` formatter. The headings formatter adds number prefixes like "1. " which break heading-text matching in detection logic. Use `strip_heading_number()` from `document_parser.py` if you need to detect headings after numbering.

### Document Parser Utilities (`app/core/document_parser.py`)

Core utilities for detecting document structure:

- `get_all_sections(doc)` — Returns list of all headed sections with start/end paragraph indices
- `get_heading_level(paragraph)` — Extracts heading level (1, 2, 3...) from paragraph style
- `find_section_by_heading(doc, heading_texts)` — Finds section by case-insensitive heading match
- `strip_heading_number(text)` — Removes number prefixes like "1. ", "1.2.3 " from text
- `is_reference_heading(text)` — Checks if text matches common reference section names
- `merge_paragraph_runs(paragraph)` — Concatenates all run texts in a paragraph

These utilities handle heading detection before AND after numbering is applied.

### Journal Configuration Schema

Each journal config JSON (`app/journal_configs/*.json`) defines all formatting rules:

```json
{
  "name": "Journal Name",
  "page_layout": { "margins": {...}, "line_spacing": 2.0, "columns": 1 },
  "fonts": { "body": {...}, "heading_1": {...}, "heading_numbering": true },
  "title_page": { "title": {...}, "authors": {...}, "affiliation": {...} },
  "abstract": { "heading_text": "Abstract", "max_words": 250, "alignment": "left", "bold_heading": true, "indent_body": 0.0, "spacing_after_heading": 6 },
  "keywords": { "heading_text": "Keywords:", "separator": ", ", "italic": false, "font_size": 12, "max_keywords": null },
  "citation_style": { "type": "numeric_bracket", "format": "[{num}]" },
  "reference_style": { "numbering": "numbered", "format": "...", "hanging_indent": 0.25 },
  "tables": { "caption_position": "above", "prefix": "TABLE", "numbering_format": "roman" },
  "figures": { "caption_position": "below", "prefix": "Fig.", "numbering_format": "arabic" },
  "equations": { "numbering": "sequential", "alignment": "center" },
  "appendix": { "format": "letter", "heading_prefix": "Appendix", "numbering_format": "{prefix} {label}" },
  "footnotes": { "numbering_format": "arabic", "font_size": 10, "max_per_page": 5 },
  "section_order": ["Introduction", "Methods", "Results", "Discussion", "Conclusion", "References"]
}
```

**Special cases**:
- Nature and PLOS ONE have `"keywords": null` (no keywords section)
- IEEE uses `"heading_prefix": "APPENDIX"` (all caps)
- Springer uses `"separator": " · "` (middot character) for keywords

## Coding Conventions

### Formatter Contract

Every formatter function in `app/formatters/` must follow this signature:

```python
def apply_<name>(doc, config) -> dict:
    """Brief description.

    Reads config["<section>"] with keys: ...

    Args:
        doc: A python-docx Document object.
        config: Journal configuration dict.

    Returns:
        dict with "warnings" (list[str]) and "stats" (dict).
    """
    warnings: list[str] = []
    # Modify doc in-place
    return {"warnings": warnings, "stats": {"<metric>": value}}
```

**Rules**:
- Modify the document in-place (never return a new Document)
- Return warnings for user-facing issues, use logger for internal errors
- Never crash the pipeline — catch exceptions and return partial results
- Stats keys must match `FormattingStats` schema in `app/api/schemas.py`
- Handle missing/null config gracefully (e.g., `config.get("keywords")` may be `None`)

### Python-docx Limitations

**Cannot modify**:
- **Footnotes** — python-docx cannot create, modify, or renumber footnotes. The `footnotes` formatter only detects and warns.
- **Multi-column layout** — python-docx cannot apply column formatting. The `layout` formatter warns users to apply columns manually in Word.
- **Track changes** — python-docx ignores tracked changes/comments.

**XML access required for**:
- Equation detection (`_has_omath_element` in `equations.py`)
- Footnote detection (`_detect_footnote_references` in `footnotes.py`)
- Use `paragraph._element.iter()` and check `element.tag.endswith('}oMath')` patterns

### Style Conventions

- **Python**: `snake_case` for variables/functions/files. Type hints on signatures. Import order: stdlib, third-party, local.
- **JavaScript**: Vanilla JS only (no frameworks). `camelCase` for variables/functions. `const`/`let`, never `var`.
- **CSS**: CSS custom properties in `:root`. BEM-like class naming.
- **Error handling**: Graceful degradation. Unparseable citations/references left as-is with warnings. Each pipeline step wrapped in try/except.
- **Journal configs**: All journal-specific rules in JSON files. NEVER hardcode journal rules in Python.
- **File management**: Uploads → `uploads/`, outputs → `output/`. Both gitignored. Use UUID filenames to avoid collisions.

## Adding New Formatters

1. Create `app/formatters/<name>.py` with `apply_<name>(doc, config)` function
2. Add import to `app/core/pipeline.py`
3. Add step to pipeline in correct order (see "Pipeline Execution Order" above)
4. Add stats fields to `FormattingStats` in `app/api/schemas.py`
5. Update stats initialization in `pipeline.py:run_pipeline()`
6. Add config section to all 6 journal configs in `app/journal_configs/`
7. Test with `uvicorn main:app --reload` and upload a sample document

## Common Patterns

### Detecting sections by heading text

```python
from app.core.document_parser import find_section_by_heading, strip_heading_number

# Find section by multiple possible heading names
section_range = find_section_by_heading(doc, ["Introduction", "Introduction:"])
if section_range:
    start_idx, end_idx = section_range
    # Process paragraphs from doc.paragraphs[start_idx:end_idx]
```

### Formatting paragraph text while preserving runs

```python
# BAD: Loses formatting runs
paragraph.text = new_text

# GOOD: Updates first run, clears others
if paragraph.runs:
    paragraph.runs[0].text = new_text
    for run in paragraph.runs[1:]:
        run.text = ""
else:
    paragraph.text = new_text
```

### Applying font formatting

```python
from docx.shared import Pt

for run in paragraph.runs:
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.italic = False
```

### Converting numbers for captions

```python
def _int_to_roman(num: int) -> str:
    """Convert integer to Roman numeral (I, II, III, IV, ...)."""
    # See tables.py or equations.py for full implementation

def _int_to_letter(num: int) -> str:
    """Convert integer to letter (A, B, C, ...)."""
    return chr(64 + num)  # 65 is 'A'
```
