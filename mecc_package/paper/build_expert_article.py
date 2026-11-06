"""Render the standalone Chinese MECC explainers to HTML and PDF."""

from pathlib import Path
import subprocess
import tempfile

import markdown


HERE = Path(__file__).resolve().parent / "current"
ARTICLES = (
    ("MECC_单卡MoE专家一日讲义.md", "一张 GPU 如何运行完整 MoE：从专家路由到 MECC"),
    ("MECC_相关工作实验与洞察详解.md", "单卡与多卡 MoE 部署：相关工作实验与洞察"),
)

CSS = r"""
@page { size: A4; margin: 18mm 17mm 17mm; }
body { font-family: 'Times New Roman', 'SimSun', serif; font-size: 11pt;
       line-height: 1.65; color: #20262c; max-width: 900px; margin: auto; }
h1, h2, h3 { color: #1d3449; break-after: avoid; }
h1 { font-size: 23pt; line-height: 1.25; margin-bottom: 4mm; }
h1 + p { font-size: 13pt; color: #38566c; margin-bottom: 9mm; }
h2 { font-size: 16pt; margin-top: 11mm; border-bottom: 1px solid #9eacb7;
     padding-bottom: 2mm; }
h3 { font-size: 12.5pt; margin-top: 7mm; }
p, li { orphans: 3; widows: 3; }
p { margin: 0 0 3.5mm; }
table { border-collapse: collapse; width: 100%; font-size: 8.3pt;
        line-height: 1.42; margin: 5mm 0; table-layout: fixed; }
tr { break-inside: avoid; }
th, td { border: 0.5pt solid #abb7c0; padding: 1.8mm 2mm;
         vertical-align: top; overflow-wrap: anywhere; }
th { background: #e9eff3; }
blockquote { border-left: 3pt solid #5b8099; padding: 2mm 4mm;
             background: #f2f6f8; margin: 4mm 0; }
pre { background: #f2f5f7; border: 0.4pt solid #d8e0e5; padding: 3mm;
      white-space: pre-wrap; font-size: 8.5pt; break-inside: avoid; }
code { font-family: Consolas, 'SimSun', monospace; font-size: .88em; }
a { color: #1d5b80; text-decoration: none; }
img { display: block; max-width: 100%; height: auto; margin: 4mm auto 2mm;
      break-inside: avoid; }
hr { border: 0; border-top: 0.5pt solid #c9d3da; margin: 6mm 0; }
"""


def main() -> None:
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if not chrome.exists():
        raise FileNotFoundError(f"Chrome unavailable: {chrome}")
    for filename, title in ARTICLES:
        source = HERE / filename
        html = source.with_suffix(".html")
        pdf = source.with_suffix(".pdf")
        body = markdown.markdown(
            source.read_text(encoding="utf-8"),
            extensions=["tables", "fenced_code", "toc"],
        )
        html.write_text(
            '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f"<title>{title}</title><style>{CSS}</style></head><body>{body}</body></html>",
            encoding="utf-8",
        )
        with tempfile.TemporaryDirectory(prefix="mecc_article_chrome_") as profile:
            subprocess.run(
                [str(chrome), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                 f"--user-data-dir={profile}", f"--print-to-pdf={pdf}", html.as_uri()],
                check=True, timeout=120, capture_output=True, text=True,
            )
        print(f"Wrote {html} and {pdf}")


if __name__ == "__main__":
    main()
