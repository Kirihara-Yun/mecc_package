"""Offline style chooser, vector comparison booklet, and reproducible archive."""
from pathlib import Path
import base64
import hashlib
import html
import json
import zipfile
import pymupdf
from build_figure_variants import SPEC, NOTES

P=Path(__file__).resolve().parent
OUT=P/'figure_variants'
STYLES=[('A','保守黑白','黑白层次、细边框、传统论文布局'),
        ('B','低饱和分析','展开对照关系，按职责或数据分面'),
        ('C','重点突出','以状态、依赖或差值组织视觉重点')]

def cn(page,rect,text,size=11,color=(.12,.17,.23)):
    page.insert_font(fontname='CN',fontfile='C:/Windows/Fonts/msyh.ttc')
    result=page.insert_textbox(pymupdf.Rect(rect),text,fontname='CN',fontsize=size,color=color)
    if result<0: raise ValueError('Gallery label does not fit: '+text)

def pdf():
    d=pymupdf.open();preview=OUT/'comparisons';preview.mkdir(exist_ok=True)
    for key,title,en,fn in SPEC:
        page=d.new_page(width=842,height=1191)
        cn(page,(32,18,810,54),title+' · 三种配图候选',20)
        cn(page,(32,56,810,84),'同一组内容与目标数据；仅比较表达方式。数值仍是假设结果。',10,color=(.45,.35,.12))
        for i,(v,label,note) in enumerate(STYLES):
            y=96+i*350
            page.draw_rect(pymupdf.Rect(28,y,814,y+337),color=(.84,.87,.90),width=.7)
            cn(page,(40,y+9,800,y+33),v+' · '+label,13)
            cn(page,(40,y+36,800,y+66),NOTES[key][i],10)
            with pymupdf.open(OUT/key/(v+'.pdf')) as source:
                page.show_pdf_page(pymupdf.Rect(40,y+72,800,y+323),source,0)
        cn(page,(32,1155,810,1178),'候选 A / B / C 可逐张混搭；示意时序不是实测时间；不把目标数字视作实验。',9,color=(.42,.45,.48))
        page.get_pixmap(matrix=pymupdf.Matrix(.9,.9)).save(str(preview/(key+'.png')))
    d.set_metadata({'title':'MECC Figure Alternatives — Hypothetical Design Targets',
                    'author':'','subject':'Three alternative encodings per figure; not measured outcomes.'})
    d.subset_fonts()
    d.save(OUT/'MECC_figure_comparison.pdf',garbage=4,deflate=True)

def web():
    sections=[];nav=[]
    for key,title,en,fn in SPEC:
        nav.append(f'<a href="#{key}">{html.escape(title)}</a>')
        cards=[]
        for i,(v,name,note) in enumerate(STYLES):
            data=base64.b64encode((OUT/key/(v+'.png')).read_bytes()).decode('ascii')
            cards.append(f'''<div class="card" id="{key}-{v}">
<header><b>{v} · {name}</b><button data-choose="{key}" data-v="{v}">选这一版</button></header>
<p>{html.escape(NOTES[key][i])}</p><button class="picture" data-zoom="{key}-{v}" aria-label="放大 {html.escape(title)} {v}"><img src="data:image/png;base64,{data}" alt="{html.escape(title)} · {v}"></button>
<small>点击图片放大 · 可与其他图混搭</small></div>''')
        sections.append(f'<section id="{key}"><h2>{html.escape(title)}</h2><div class="cards">'+''.join(cards)+'</div></section>')
    index=json.dumps([{'key':x[0],'title':x[1]} for x in SPEC],ensure_ascii=False)
    page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MECC 配图候选：逐张选择 A / B / C</title><style>
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:90px}body{margin:0;background:#f4f6f9;color:#263747;font:15px/1.7 "Microsoft YaHei","PingFang SC",sans-serif}.wrap{max-width:1600px;margin:auto;padding:28px}h1{font-size:27px;margin:0 0 10px}h2{font-size:21px;margin:34px 0 14px}.lead{max-width:1050px;color:#546678}.notice{background:#fff4c3;border-left:4px solid #d0a33d;padding:10px 16px;margin:18px 0}.nav{position:sticky;top:0;z-index:3;display:flex;gap:8px;flex-wrap:wrap;background:#f4f6f9f5;padding:12px 0;border-bottom:1px solid #dde4eb}.nav a{font-size:13px;text-decoration:none;color:#245b8a;background:white;border:1px solid #dae2e9;border-radius:5px;padding:5px 10px}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.card{background:white;border:2px solid #e0e6ed;border-radius:8px;padding:17px;min-width:0}.card.selected{border-color:#245b8a;box-shadow:0 0 0 2px #245b8a15}.card header{display:flex;align-items:center;justify-content:space-between;gap:8px}.card p{font-size:13px;color:#657484;min-height:46px;margin:12px 0}.card small{font-size:11px;color:#7d8995}button{font:inherit;font-size:12px;padding:5px 10px;color:#245b8a;background:#f8fbfe;border:1px solid #c7d7e5;border-radius:4px;cursor:pointer}.picture{display:flex;align-items:center;justify-content:center;background:white;border:0;width:100%;height:280px;padding:0;margin:8px 0 14px}.picture img{max-width:100%;max-height:100%;object-fit:contain}.selection{background:white;border:1px solid #dce4ec;border-radius:8px;margin-top:40px;padding:22px}textarea{width:100%;height:240px;font:14px/1.8 Consolas,"Microsoft YaHei",monospace;padding:12px;border:1px solid #d3dde7;border-radius:5px;color:#263747;resize:vertical}.actions{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}dialog{border:1px solid #cdd9e4;border-radius:8px;padding:16px;max-width:97vw;max-height:95vh}dialog::backdrop{background:#132b46aa}dialog header{display:flex;justify-content:space-between;gap:20px;margin-bottom:12px}dialog img{display:block;max-width:92vw;max-height:82vh;object-fit:contain}.foot{font-size:12px;color:#7b8995;margin:20px 0}@media(max-width:1100px){.cards{grid-template-columns:1fr}.picture{height:auto;min-height:180px}.picture img{max-height:430px}.wrap{padding:16px}.nav{position:static}.card p{min-height:0}}
</style></head><body><main class="wrap"><h1>MECC 配图候选：逐张选择 A / B / C</h1>
<p class="lead">7 张正文图 + 1 张资源补充图，每张 3 版，共 24 张。差异包括布局、视觉编码和信息组织，并非只换颜色。A 偏保守黑白，B 偏低饱和分析，C 偏重点突出。可以逐张混搭。</p>
<div class="notice">所有实验数值仍为假设目标；示意图不代表真实时间或已验证的内存配置。三版使用同一份数据。放大图可查看小字，独立 PDF/SVG 保留在配套文件夹中。</div>
<nav class="nav">'''+''.join(nav)+'''</nav>'''+''.join(sections)+'''
<section class="selection"><h2>你的选择清单 <span id="count"></span></h2><p>逐张点击“选这一版”。也可以先统一选择，再单独调整。选好后把下面的清单发给我。</p>
<div class="actions"><button data-all="A">全部先选 A</button><button data-all="B">全部先选 B</button><button data-all="C">全部先选 C</button><button id="download">下载选择清单</button></div><textarea id="result" readonly aria-label="选择清单"></textarea></section>
<p class="foot">图片已内嵌，可离线打开；选择仅保存在当前浏览器本地，不向服务器发送。不同版式长宽比不同，确定后再放回论文统一排版。</p></main>
<dialog id="zoom"><header><b id="zoom-title"></b><button id="close">关闭</button></header><img id="zoom-image" alt="放大预览"></dialog>
<script>const figures='''+index+''';let chosen={};try{chosen=JSON.parse(localStorage.getItem('mecc-figure-choice-v1')||'{}')}catch(e){}const result=document.getElementById('result');function update(){document.querySelectorAll('.card').forEach(c=>c.classList.remove('selected'));for(const f of figures){const v=chosen[f.key];if(v&&document.getElementById(f.key+'-'+v))document.getElementById(f.key+'-'+v).classList.add('selected')}result.value='MECC 配图选择清单\\n'+figures.map(f=>f.title+'：'+(chosen[f.key]||'未选择')).join('\\n');document.getElementById('count').textContent='('+figures.filter(f=>chosen[f.key]).length+'/8)';try{localStorage.setItem('mecc-figure-choice-v1',JSON.stringify(chosen))}catch(e){}}document.querySelectorAll('[data-choose]').forEach(b=>b.onclick=()=>{chosen[b.dataset.choose]=b.dataset.v;update()});document.querySelectorAll('[data-all]').forEach(b=>b.onclick=()=>{figures.forEach(f=>chosen[f.key]=b.dataset.all);update()});const zoom=document.getElementById('zoom');document.querySelectorAll('[data-zoom]').forEach(b=>b.onclick=()=>{document.getElementById('zoom-image').src=b.querySelector('img').src;document.getElementById('zoom-title').textContent=b.querySelector('img').alt;zoom.showModal()});document.getElementById('close').onclick=()=>zoom.close();zoom.onclick=e=>{if(e.target===zoom)zoom.close()};document.getElementById('download').onclick=()=>{const url=URL.createObjectURL(new Blob([result.value],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='MECC_配图选择.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};update();</script></body></html>'''
    (OUT/'MECC_figure_chooser.html').write_text(page,encoding='utf-8')

def audit():
    checks=[]
    for key,cn_title,en,fn in SPEC:
        for v,label,note in STYLES:
            p=OUT/key/(v+'.pdf');d=pymupdf.open(p);page=d[0]
            outside=[]
            for b in page.get_text('dict')['blocks']:
                for line in b.get('lines',[]):
                    for span in line['spans']:
                        if not page.rect.contains(pymupdf.Rect(span['bbox'])):outside.append(span['text'])
            text=page.get_text();hypo=key not in ['02_framework','03_retention','04_delivery']
            checks.append({'figure':key,'variant':v,'vector_only':not page.get_images(),
             'text_in_bounds':not outside,'outside_text':outside,
             'hypothetical_notice':not hypo or 'HYPOTHETICAL' in text,
             'width_inches':round(page.rect.width/72,2),'height_inches':round(page.rect.height/72,2)})
    report={'scope':'Asset completeness, vector output and clipping checks; not acceptance certification',
            'entries':checks,'passed':all(x['vector_only'] and x['text_in_bounds'] and x['hypothetical_notice'] for x in checks)}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert report['passed'],report

def main():
    audit();pdf();web()
    files=[f for f in OUT.rglob('*') if f.is_file()]
    with zipfile.ZipFile(P.parent/'MECC_figure_variants.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in files:z.write(f,'figure_variants/'+f.relative_to(OUT).as_posix())
    print('Saved chooser HTML, 8-page comparison PDF, previews, and separate variants archive.')

if __name__=='__main__':main()
