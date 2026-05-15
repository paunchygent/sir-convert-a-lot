"""Exam.net PDF renderer document HTML assembly.

Purpose:
    Assemble full HTML documents for the Exam.net-oriented PDF renderer from
    already-rendered item sections.

Relationships:
    - Consumes item sections from `domain.digiexam_examnet_pdf_items`.
    - Feeds `infrastructure.digiexam_examnet_pdf_renderer` through the thin
      document coordinator.
"""

from __future__ import annotations

from html import escape

from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfItemRender,
)


def build_examnet_pdf_html(
    *,
    source_filename: str,
    items: tuple[DigiExamExamNetPdfItemRender, ...],
) -> str:
    """Build the complete HTML document rendered by WeasyPrint."""

    item_html = "\n".join(item.html for item in items)
    return f"""<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<title>{escape(source_filename)} Exam.net PDF Import</title>
<style>
@page {{
  size: A4;
  margin: 18mm 16mm;
}}
body {{
  color: #111;
  font-family: Arial, sans-serif;
  font-size: 12pt;
  line-height: 1.35;
}}
.exam-item {{
  break-inside: avoid;
  margin: 0 0 18pt;
}}
h2 {{
  font-size: 15pt;
  margin: 0 0 6pt;
}}
p {{
  margin: 0 0 6pt;
}}
.points,
.item-type,
.answer-key {{
  font-weight: 700;
}}
.prompt {{
  margin: 8pt 0;
}}
.prompt-image {{
  display: block;
  margin: 6pt 0;
  max-width: 100%;
}}
.gap-placeholder {{
  border-bottom: 1pt solid #111;
  display: inline-block;
  min-width: 42pt;
  text-align: center;
}}
.options {{
  margin: 8pt 0 8pt 18pt;
}}
.options p {{
  margin: 0 0 5pt;
}}
</style>
</head>
<body>
<main>
{item_html}
</main>
</body>
</html>
"""
