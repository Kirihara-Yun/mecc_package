"""Build an offline Chinese reading guide from Markdown; embed its figures."""
from pathlib import Path
import base64
import hashlib
import html
import re
import markdown
from markdown.extensions.toc import slugify_unicode

P=Path(__file__).resolve().parent
SOURCE=P/'MECC_BEGINNER_GUIDE_ZH.md'
TARGET=P/'MECC_BEGINNER_GUIDE_ZH.html'
CSS='''
:root{color-scheme:light;--ink:#23303c;--blue:#245b8a;--rule:#dce3e9}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}
body{margin:0;background:#f5f7fa;color:var(--ink);font-family:"Microsoft YaHei",
 "PingFang SC","Noto Sans CJK SC",sans-serif;font-size:17px;line-height:1.95}
.layout{max-width:1320px;margin:32px auto;display:grid;grid-template-columns:245px minmax(0,1fr);gap:28px;padding:0 22px}
nav{position:sticky;top:24px;align-self:start;max-height:92vh;overflow:auto;font-size:13px;line-height:1.65;padding:10px 12px 20px}
nav strong{display:block;font-size:15px;margin-bottom:12px}nav ul{list-style:none;padding-left:12px}nav li{margin:9px 0}nav a{text-decoration:none;color:#4d6071}nav a:hover{color:var(--blue)}
article{min-width:0;background:white;padding:42px 48px 50px;border:1px solid var(--rule);border-radius:9px;box-shadow:0 4px 24px #21374b08}
h1{font-size:30px;line-height:1.55;margin:10px 0 24px;color:#163e60}
h2{font-size:24px;line-height:1.6;margin:48px 0 20px;padding-bottom:8px;border-bottom:1px solid var(--rule)}
h3{font-size:19px;margin:30px 0 12px;line-height:1.65}p{margin:15px 0}strong{color:#183e5b}
a{color:var(--blue);text-underline-offset:3px}ul,ol{padding-left:1.6em}li{margin:8px 0}
blockquote{margin:24px 0;padding:10px 22px;border-left:4px solid #6a9abf;background:#f1f6fa}
blockquote.status{background:#fff8d7;border-left-color:#d6a832}blockquote p{margin:8px 0}
code{font-family:Consolas,"Microsoft YaHei",monospace;font-size:.9em;background:#eef3f7;border-radius:3px;padding:2px 5px}
pre{overflow:auto;background:#eef3f7;padding:17px;border-radius:5px;line-height:1.8}pre code{padding:0}
table{width:100%;border-collapse:collapse;margin:24px 0;font-size:14px;line-height:1.8}
th,td{border-bottom:1px solid var(--rule);padding:11px 10px;text-align:left;vertical-align:top}th{background:#edf3f8;color:#1c405b}tr:last-child td{border-bottom:2px solid #bbcbd7}
img{display:block;max-width:100%;height:auto;margin:26px auto;padding:12px 5px;background:white;border:1px solid #e4e9ee;border-radius:4px}
details{margin:16px 0 24px;padding:12px 17px;border:1px solid var(--rule);border-radius:5px;background:#f7fafc}summary{cursor:pointer;color:var(--blue);font-weight:600}details p{font-size:16px}
.edition{font-size:12px;color:#6f7e8b;margin-bottom:18px}.tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:25px}.badge{padding:3px 10px;background:#fff3b0;border:1px solid #efdc8c;border-radius:4px;font-size:12px}button{font:inherit;font-size:12px;border:1px solid #cad6df;background:white;padding:4px 11px;border-radius:4px;cursor:pointer}
.footnote{font-size:12px;color:#75818b;border-top:1px solid var(--rule);padding-top:20px;margin-top:38px}
@media(max-width:950px){.layout{display:block;padding:0 12px;margin:16px auto}nav{position:static;max-height:250px;margin-bottom:20px}article{padding:27px 23px}h1{font-size:25px}h2{font-size:22px}body{font-size:16px}table{font-size:13px}}
@media print{@page{size:A4;margin:18mm}body{background:white;font-size:11pt;line-height:1.75}.layout{display:block;margin:0;padding:0}nav,.tools{display:none}article{padding:0;border:0;box-shadow:none}h1{font-size:21pt}h2{font-size:16pt;break-after:avoid}h3{font-size:13pt;break-after:avoid}table{font-size:9pt}img,table,details{break-inside:avoid}details{display:block}a{color:inherit;text-decoration:none}.status{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
'''

def main():
    source=SOURCE.read_text(encoding='utf-8')
    md=markdown.Markdown(extensions=['tables','fenced_code','toc'],
        extension_configs={'toc':{'toc_depth':'2','slugify':slugify_unicode}})
    body=md.convert(source).replace('<blockquote>','<blockquote class="status">',1)
    embedded=[]
    def embed(match):
        url=html.unescape(match[1]); f=(P/url).resolve()
        if not f.is_relative_to(P) or not f.is_file():
            raise ValueError(f'Missing or unexpected figure: {url}')
        mime={'.png':'image/png','.svg':'image/svg+xml'}[f.suffix.lower()]
        embedded.append(url)
        return 'src="data:'+mime+';base64,'+base64.b64encode(f.read_bytes()).decode('ascii')+'"'
    body=re.sub(r'src="([^"]+)"',embed,body)
    digest=hashlib.sha256(source.encode('utf-8')).hexdigest()
    page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>从零读懂 MECC：中文论文解读</title><style>'''+CSS+'''</style></head>
<body><div class="layout"><nav aria-label="章节导航"><strong>阅读导航</strong>'''+md.toc+'''</nav><article>
<div class="edition">配套版本：MECC DAC 2027 polished draft · 更新于 2026-10-29</div>
<div class="tools"><span class="badge">设计稿解读 · 性能数值仍是假设目标</span><button type="button" onclick="window.print()">打印 / 另存为 PDF</button></div>
'''+body+'''<p class="footnote">配图已嵌入本文件，可离线阅读。其他仓库文档链接需保留相应目录。源文档 SHA-256：'''+digest+'''</p></article></div></body></html>'''
    TARGET.write_text(page,encoding='utf-8')
    print(f'Generated {TARGET.name}; {len(embedded)} embedded figures; {len(source)} source characters.')

if __name__=='__main__': main()
