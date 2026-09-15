#!/usr/bin/env python3
"""Render review markdown to print-ready PDF via headless Chromium."""
import markdown, subprocess, sys, os, pathlib

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

CSS = """
@page { size: A4; margin: 20mm 18mm 18mm 18mm; }
html { -webkit-print-color-adjust: exact; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt;
       line-height: 1.5; color: #1a1a1a; margin: 0; }
h1 { font-size: 19pt; line-height:1.2; margin: 0 0 4pt; letter-spacing: -0.2pt; }
h2 { font-size: 13pt; margin: 15pt 0 5pt; padding-bottom: 3pt;
     border-bottom: 1px solid #c8c8c8; page-break-after: avoid; }
h3 { font-size: 11pt; margin: 14pt 0 4pt; page-break-after: avoid;
     font-family: 'Helvetica Neue', Arial, sans-serif; }
h1 + p, h2 + p, h3 + p { margin-top: 4pt; }
p { margin: 0 0 7pt; }
ul, ol { margin: 0 0 8pt; padding-left: 18pt; }
li { margin-bottom: 3pt; }
blockquote { margin: 7pt 0 9pt; padding: 7pt 12pt; border-left: 3px solid #999;
             background: #f6f6f4; font-style: normal; page-break-inside: avoid; }
blockquote p { margin: 0 0 5pt; }
blockquote p:last-child { margin-bottom: 0; }
code { font-family: 'SF Mono', Menlo, Consolas, monospace; font-size: 9pt;
       background: #eeeeec; padding: 0 2px; border-radius: 2px; }
hr { border: 0; border-top: 1px solid #c8c8c8; margin: 16pt 0; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0 10pt;
        font-size: 9.5pt; page-break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 4pt 6pt; text-align: left;
         vertical-align: top; }
th { background: #efefec; font-family: 'Helvetica Neue', Arial, sans-serif;
     font-size: 9pt; }
strong { font-weight: 700; }
a { color: #1a1a1a; }
.pagebreak { page-break-after: always; }
/* The cover must be exactly one page; the claim pages stay at reading size. */
.cover { font-size: 9.9pt; line-height: 1.4; }
.cover h1 { font-size: 17pt; }
.cover h2 { font-size: 11.8pt; margin: 12pt 0 4pt; }
.cover p { margin: 0 0 6pt; }
table.sig { margin-top: 14pt; }
table.sig td { height: 40pt; }
"""

COMPACT = """
@page { margin: 14mm 15mm 12mm 15mm; }
body { font-size: 9.2pt; line-height: 1.34; }
h1 { font-size: 16pt; }
h2 { font-size: 11.5pt; margin: 12pt 0 4pt; }
h3 { font-size: 9.8pt; margin: 9pt 0 3pt; }
p { margin: 0 0 5pt; }
blockquote { margin: 5pt 0 6pt; padding: 5pt 9pt; font-size: 8.8pt;
             line-height: 1.3; }
table { margin: 5pt 0 7pt; font-size: 8.8pt; }
th, td { padding: 2.5pt 5pt; }
hr { margin: 10pt 0; }
"""


def render(md_paths, out_pdf, title, compact=False):
    html_parts = []
    for i, p in enumerate(md_paths):
        txt = pathlib.Path(p).read_text(encoding="utf-8")
        body = markdown.markdown(txt, extensions=["tables", "sane_lists", "md_in_html"])
        html_parts.append(body)
        if i < len(md_paths) - 1:
            html_parts.append('<div class="pagebreak"></div>')
    css = CSS + (COMPACT if compact else "")
    html = ("<!doctype html><html><head><meta charset='utf-8'>"
            "<title>%s</title><style>%s</style></head><body>%s</body></html>"
            % (title, css, "\n".join(html_parts)))
    tmp = "/tmp/_render_%s.html" % os.path.basename(out_pdf).replace(".pdf", "")
    pathlib.Path(tmp).write_text(html, encoding="utf-8")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                    "--no-pdf-header-footer", "--print-to-pdf=" + out_pdf,
                    "file://" + tmp], check=True, capture_output=True)
    print("%s  %.1f KB" % (out_pdf, os.path.getsize(out_pdf) / 1024))

if __name__ == "__main__":
    compact = "--compact" in sys.argv
    args = [a for a in sys.argv[2:] if a != "--compact"]
    render(args, sys.argv[1], "review", compact=compact)

# Regenerate both review PDFs:
#   python3 reports/render_review_pdf.py reports/claim-bank-review.pdf \
#           reports/claim-bank-cover.md reports/claim-bank-review.md
#   python3 reports/render_review_pdf.py reports/topic-set-review.pdf \
#           reports/topic-set-review.md --compact
