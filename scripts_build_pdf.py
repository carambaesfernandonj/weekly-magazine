import io, json, re, urllib.request
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak

ARTICLES=Path('data/articles.json'); EDITORIAL=Path('data/editorial.json'); OUT_DIR=Path('data/issues')
def load(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return d
def esc(x):
    return str(x or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def img_from_url(url,max_w,max_h):
    try:
        if not str(url).startswith(('http://','https://')): return None
        req=urllib.request.Request(url,headers={'User-Agent':'WEEKLY-PDF/0.9.19'})
        with urllib.request.urlopen(req,timeout=12) as r: raw=r.read(3_000_000)
        from PIL import Image as PILImage
        bio=io.BytesIO(raw); im=PILImage.open(bio); w,h=im.size
        if not w or not h:return None
        scale=min(max_w/w,max_h/h,1)
        return Image(bio,width=w*scale,height=h*scale)
    except Exception:return None
def blocks(a):
    out=[]
    for b in a.get('contentBlocks') or []:
        t=str((b or {}).get('text') or '').strip()
        if t: out.append((str((b or {}).get('type') or 'p').lower(),t))
    if not out and a.get('contentText'):
        out=[('p',x.strip()) for x in re.split(r'\n\s*\n',str(a['contentText'])) if x.strip()]
    if not out and a.get('description'): out=[('p',str(a['description']).strip())]
    return out
def images(a):
    vals=[a.get('image')]
    vals += [x.get('url') if isinstance(x,dict) else x for x in (a.get('images') or [])]
    seen=set(); out=[]
    for u in vals:
        if u and u not in seen:seen.add(u);out.append(u)
    return out[:5]
def footer(c,d,issue):
    c.saveState();c.setFont('Helvetica',7.5);c.setFillColor(colors.HexColor('#666666'))
    c.drawString(18*mm,10*mm,f'WEEKLY · EDICIÓN #{issue}');c.drawRightString(192*mm,10*mm,str(d.page));c.restoreState()

data=load(ARTICLES,{}); ed=load(EDITORIAL,{})
if not ed.get('locked'): raise SystemExit('No hay edición cerrada; PDF omitido.')
issue=ed.get('issueNumber','?'); OUT_DIR.mkdir(parents=True,exist_ok=True); out=OUT_DIR/f'issue-{issue}.pdf'
ss=getSampleStyleSheet(); cover=ParagraphStyle('cover',parent=ss['Title'],fontName='Helvetica-Bold',fontSize=28,leading=31,spaceAfter=8); kick=ParagraphStyle('kick',parent=ss['Normal'],fontName='Helvetica-Bold',fontSize=9,leading=11,textColor=colors.HexColor('#555555'),spaceAfter=7); h=ParagraphStyle('h',parent=ss['Heading1'],fontName='Helvetica-Bold',fontSize=21,leading=23,spaceAfter=9); dek=ParagraphStyle('dek',parent=ss['Normal'],fontSize=11,leading=15,textColor=colors.HexColor('#444444'),spaceAfter=11); body=ParagraphStyle('body',parent=ss['BodyText'],fontSize=10.5,leading=15,spaceAfter=9); sub=ParagraphStyle('sub',parent=ss['Heading2'],fontName='Helvetica-Bold',fontSize=14,leading=17,spaceBefore=8,spaceAfter=6); small=ParagraphStyle('small',parent=ss['Normal'],fontSize=8,leading=10,textColor=colors.HexColor('#666666'),spaceAfter=5)
story=[Paragraph('WEEKLY',cover),Paragraph(f'EDICIÓN #{esc(issue)}',kick)]
w=ed.get('issueWindow') or {}; story.append(Paragraph(f"{esc(w.get('start'))} — {esc(w.get('end'))}",small))
# Use the AI cover only if it is a local/generated file; otherwise the PDF remains clean and text-led.
ci=ed.get('coverImage','')
if str(ci).startswith(('http://','https://')):
    im=img_from_url(ci,150*mm,170*mm)
    if im: story += [im,Spacer(1,8)]
story.append(Paragraph(esc(ed.get('headline') or 'DESDE LA REDACCIÓN'),h))
for p in re.split(r'\n\s*\n',str(ed.get('editorial') or '').strip()):
    if p.strip():story.append(Paragraph(esc(p).replace('\n','<br/>'),body))
story += [Spacer(1,10),Paragraph('WEEKLY · EDICIÓN CERRADA',kick),PageBreak()]
arts=data.get('articles',[]); ids=ed.get('selected_ids') or []
sel=[]
for i in ids:
    if isinstance(i,int) and 0<=i<len(arts):sel.append(arts[i])
for n,a in enumerate(sel,1):
    story += [Paragraph(esc((a.get('category') or 'OTROS')).upper(),kick),Paragraph(esc(a.get('title') or 'Sin título'),h)]
    if a.get('description'):story.append(Paragraph(esc(a['description']),dek))
    ims=images(a)
    if ims:
        im=img_from_url(ims[0],165*mm,85*mm)
        if im:story += [im,Spacer(1,7)]
    for typ,text in blocks(a):story.append(Paragraph(esc(text).replace('\n','<br/>'),sub if typ in {'h2','h3','heading'} else body))
    if a.get('link'):story.append(Paragraph('LEER ORIGINAL · '+esc(a['link']),small))
    if n<len(sel):story.append(PageBreak())

doc=SimpleDocTemplate(str(out),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=16*mm,bottomMargin=15*mm,title=f'WEEKLY #{issue}',author='WEEKLY')
doc.build(story,onFirstPage=lambda c,d:footer(c,d,issue),onLaterPages=lambda c,d:footer(c,d,issue));print(out)
