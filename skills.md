---
name: manuscript-formatter
description: Formats research papers for Springer, Elsevier, and Emerald journals.
allowed-tools: ["Read", "Write", "Edit", "Bash"]
---

# Manuscript Formatting Instructions
When this skill is invoked via `/manuscript-formatter` or when I ask to format a paper:

## Journal Style Guides
- **Springer:** Use the 'Springer Nature' LaTeX template standards. Ensure references are in 'Numbered' or 'Name-Year' format as requested.
- **Elsevier:** Follow 'Article' class rules. Ensure the 'Declaration of Interest' section is included.
- **Emerald:** Use the Harvard referencing style and ensure the 'Structured Abstract' (Purpose, Design, Findings, etc.) is exactly 250 words.

## Automation Steps
1. Read the current manuscript file.
2. Check for missing sections required by the target journal.
3. Reformat the bibliography using the correct citation style.
4. Run a `pdflatex` or similar check if a LaTeX environment is available.
