import io, json, re, urllib.request
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

ROOT=Path('.')
ARTICLES=ROOT/'data/articles.json'
EDITORIAL=ROOT/'data/editorial.json'
OUT_DIR=ROOT/'data/issues'
INDEX=OUT_DIR/'index.json'
ASSETS=ROOT/'assets'

W,H=A4
M=18*2.83465
BG=colors.HexColor('#eeeae1')
INK=colors.HexColor('#17191b')
MUTED=colors.HexColor('#66625b')
LINE=colors.HexColor('#aaa59c')
ACID=colors.HexColor('#c8ff31')
DARK=colors.HexColor('#17191b')
DARK_TEXT=colors.HexColor('#eeeae1')


def load(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return d

def esc(x):
    return str(x or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def article_title(a):
    return str(a.get('title') or 'Sin título').strip()

def story_blocks(a):
    blocks=[]
    for b in a.get('contentBlocks') or []:
        if not isinstance(b,dict): continue
        t=str(b.get('text') or '').strip()
        if t: blocks.append((str(b.get('type') or 'p').lower(),t))
    if not blocks and a.get('contentText'):
        blocks=[('p',x.strip()) for x in re.split(r'\n\s*\n',str(a['contentText'])) if x.strip()]
    if not blocks and a.get('description'):
        blocks=[('p',str(a['description']).strip())]
    return blocks

def article_images(a):
    vals=[]
    if a.get('image'): vals.append(a['image'])
    for x in a.get('images') or []:
        vals.append(x.get('url') if isinstance(x,dict) else x)
    out=[]; seen=set()
    for u in vals:
        if not u: continue
        u=str(u).strip()
        if not u or u in seen: continue
        seen.add(u); out.append(u)
    return out[:6]

_IMAGE_CACHE={}
def fetch_image(url):
    key=str(url)
    if key in _IMAGE_CACHE:return _IMAGE_CACHE[key]
    try:
        if str(url).startswith(('http://','https://')):
            import subprocess, tempfile
            with tempfile.NamedTemporaryFile(suffix='.img') as tmp:
                r=subprocess.run(['curl','-L','--silent','--show-error','--location','--connect-timeout','1','--max-time','3','-A','WEEKLY-PDF/0.9.22',str(url),'-o',tmp.name],capture_output=True,timeout=4)
                if r.returncode==0:
                    raw=Path(tmp.name).read_bytes()
                    if raw:
                        _IMAGE_CACHE[key]=raw; return raw
        p=ROOT/str(url).lstrip('./')
        if p.exists():
            raw=p.read_bytes(); _IMAGE_CACHE[key]=raw; return raw
    except Exception:
        pass
    _IMAGE_CACHE[key]=None
    return None

def image_reader(url):
    raw=fetch_image(url)
    if not raw:return None
    try:return ImageReader(io.BytesIO(raw))
    except Exception:return None

def draw_image(c,url,x,y,w,h,contain=False):
    ir=image_reader(url)
    if not ir:return False
    try:
        iw,ih=ir.getSize()
        if iw<=0 or ih<=0:return False
        scale=min(w/iw,h/ih)
        dw,dh=iw*scale,ih*scale
        if not contain:
            # Fill the box while keeping the focal crop centered.
            scale=max(w/iw,h/ih); dw,dh=iw*scale,ih*scale
        dx=x+(w-dw)/2; dy=y+(h-dh)/2
        c.saveState(); c.rect(x,y,w,h,stroke=0,fill=1)
        c.setFillColor(colors.HexColor('#d8d2c7')); c.rect(x,y,w,h,stroke=0,fill=1)
        c.drawImage(ir,dx,dy,width=dw,height=dh,preserveAspectRatio=False,mask='auto')
        c.restoreState(); return True
    except Exception:return False

def style(name,size,leading,font='Helvetica',color=INK,space=0):
    return ParagraphStyle(name,fontName=font,fontSize=size,leading=leading,textColor=color,spaceAfter=space,allowWidows=0,allowOrphans=0)

BODY=style('body',10.4,14.6,'Times-Roman',INK,7)
BODY_DARK=style('bodydark',10.4,14.6,'Times-Roman',DARK_TEXT,7)
DEK=style('dek',10.4,14,'Helvetica-Bold',colors.HexColor('#4d4a45'),8)
DEK_DARK=style('dekdark',10.4,14,'Helvetica-Bold',colors.HexColor('#bdb8ae'),8)
SUB=style('sub',14,15,'Helvetica-Bold',INK,7)
SUB_DARK=style('subdark',14,15,'Helvetica-Bold',DARK_TEXT,7)
SMALL=style('small',7.2,9,'Helvetica-Bold',MUTED,2)
QUOTE=style('quote',18,20,'Helvetica-Bold',INK,8)
DARK_TITLE=style('darktitle',38,35,'Helvetica-Bold',DARK_TEXT,7)

def draw_running(c,source,date,dark=False):
    c.setStrokeColor(colors.HexColor('#55524c') if dark else INK); c.setLineWidth(0.8); c.line(M,H-M-5,W-M,H-M-5)
    c.setFillColor(colors.HexColor('#aaa69e') if dark else MUTED); c.setFont('Helvetica-Bold',7)
    c.drawString(M,H-M+3,str(source or 'WEEKLY').upper()[:70])
    c.drawRightString(W-M,H-M+3,str(date or '')[:10])

def draw_page_number(c,n,dark=False):
    c.setFillColor(colors.HexColor('#343840') if dark else MUTED); c.setFont('Helvetica-Bold',7)
    c.drawString(M,12,str(n).zfill(2))

def new_page(c,dark=False):
    c.setFillColor(DARK if dark else BG); c.rect(0,0,W,H,stroke=0,fill=1)

def draw_paragraph(c,text,x,y,w,available,sty):
    p=Paragraph(esc(text).replace('\n','<br/>'),sty)
    ww,hh=p.wrap(w,available)
    if hh>available+0.5:return None
    p.drawOn(c,x,y-hh); return hh

def draw_split_paragraph(c,text,x,y,w,available,sty):
    p=Paragraph(esc(text).replace('\n','<br/>'),sty)
    parts=p.split(w,available)
    if not parts:return [],text
    first=parts[0]
    ww,hh=first.wrap(w,available); first.drawOn(c,x,y-hh)
    # Recover remaining text approximately by using Paragraph fragments is awkward; use a sentence/word splitter fallback.
    rendered=first.getPlainText() if hasattr(first,'getPlainText') else ''
    if not rendered or len(rendered)>=len(text): return [hh],''
    rem=text[len(rendered):].lstrip()
    return [hh],rem

def wrap_title(c,text,x,y,w,max_size=34,min_size=19,leading_ratio=.92):
    size=max_size
    while size>min_size:
        # Approximate line count by character width; then Paragraph does the exact wrapping.
        st=style('title',size,size*leading_ratio,'Helvetica-Bold',INK,7)
        p=Paragraph(esc(text),st); ww,hh=p.wrap(w,180)
        if hh<=180:return p,hh
        size-=1.5
    st=style('titlemin',min_size,min_size*leading_ratio,'Helvetica-Bold',INK,7)
    p=Paragraph(esc(text),st); ww,hh=p.wrap(w,180); return p,hh

def draw_footer(c,issue,n,dark=False):
    c.setFillColor(colors.HexColor('#aaa69e') if dark else MUTED); c.setFont('Helvetica-Bold',6.8)
    c.drawString(M,8,f'WEEKLY · EDICIÓN #{issue}')
    c.drawRightString(W-M,8,'PERSONAL EDITION')
    draw_page_number(c,n,dark)

def draw_fallback_cover(c,issue,headline,date,cover_y):
    x=M; y=cover_y; w=W-2*M; h=235
    c.setFillColor(colors.HexColor('#c8ff31')); c.rect(x,y,w,h,stroke=0,fill=1)
    c.setFillColor(INK); c.setFont('Helvetica-Bold',58); c.drawString(x+18,y+h-70,'WEEKLY')
    c.setFont('Helvetica-Bold',26); c.drawString(x+18,y+h-108,f'#{issue}')
    c.setLineWidth(5); c.line(x+20,y+40,x+w-20,y+40)
    c.setFont('Helvetica-Bold',9); c.drawString(x+20,y+22,'EDICIÓN PERSONAL · REVISTA SEMANAL')
    return y

def draw_cover(c,ed,stories,n):
    new_page(c,False)
    issue=ed.get('issueNumber','—'); headline=ed.get('headline') or article_title(stories[0]) if stories else 'WEEKLY'
    c.setFillColor(INK); c.setFont('Helvetica-Bold',9); c.drawString(M,H-M+2,'WEEKLY'); c.drawRightString(W-M,H-M+2,f'EDICIÓN #{issue}')
    c.setStrokeColor(INK); c.line(M,H-M-6,W-M,H-M-6)
    y=H-M-28
    c.setFillColor(MUTED); c.setFont('Helvetica-Bold',7); c.drawString(M,y,'EDICIÓN SEMANAL · REVISTA PERSONAL'); y-=14
    p,hh=wrap_title(c,headline,M,y,W-2*M,36,21); p.drawOn(c,M,y-hh); y-=hh+15
    date=(ed.get('issueWindow') or {}).get('start','')+' — '+(ed.get('issueWindow') or {}).get('end','')
    c.setFillColor(MUTED); c.setFont('Helvetica',8.5); c.drawString(M,y,date); y-=14
    cover=ed.get('coverImage') or 'assets/weekly-cover-fallback.svg'
    cover_y=y-245
    if not draw_image(c,cover,M,cover_y,W-2*M,235,contain=False):
        draw_fallback_cover(c,issue,headline,date,cover_y)
    else:
        c.setFillColor(ACID); c.setFont('Helvetica-Bold',7); c.drawString(M+7,cover_y+7,'PORTADA')
    y=cover_y-18
    c.setStrokeColor(INK); c.line(M,y,W-M,y); y-=12
    c.setFillColor(INK); c.setFont('Helvetica-Bold',7); c.drawString(M,y,f'{len(stories)} HISTORIAS · {len({str(a.get("source")) for a in stories if a.get("source")})} FUENTES')
    c.setFillColor(MUTED); c.setFont('Helvetica',7); c.drawRightString(W-M,y,'EDICIÓN CERRADA')
    draw_footer(c,issue,n,False); c.showPage()

def draw_editorial(c,ed,n):
    new_page(c,True); issue=ed.get('issueNumber','—'); draw_running(c,'WEEKLY · DESDE LA REDACCIÓN',str((ed.get('issueWindow') or {}).get('start','')),True)
    y=H-M-30; c.setFillColor(ACID); c.setFont('Helvetica-Bold',8); c.drawString(M,y,'DESDE LA REDACCIÓN'); y-=16
    title=ed.get('headline') or 'DESDE LA REDACCIÓN'; p=Paragraph(esc(title),DARK_TITLE); _,hh=p.wrap(W-2*M,170); p.drawOn(c,M,y-hh); y-=hh+15
    editorial=str(ed.get('editorial') or '').strip()
    body=BODY_DARK
    for para in re.split(r'\n\s*\n',editorial):
        para=para.strip()
        if not para:continue
        p=Paragraph(esc(para).replace('\n','<br/>'),body); ww,ph=p.wrap(W-2*M,y-65)
        if ph>y-65: break
        p.drawOn(c,M,y-ph); y-=ph+6
    c.setFillColor(ACID); c.setFont('Helvetica-Bold',8); c.drawString(M,38,'FERNANDON™ · EDITORIAL' if ed.get('editorialSource')=='ai' else 'WEEKLY · MANIFIESTO')
    draw_footer(c,issue,n,True); c.showPage()

def draw_section(c,a,n,section_no):
    new_page(c,False); issue=section_name(a); draw_running(c,f'WEEKLY · {issue}',str(a.get('published',''))[:10],False)
    y=H-M-38; c.setFillColor(INK); c.setFont('Helvetica-Bold',8); c.drawString(M,y,f'SECCIÓN {section_no:02d}'); y-=35
    c.setFont('Helvetica-Bold',78); c.setFillColor(colors.HexColor('#c3beb4')); c.drawRightString(W-M,y,issue[:1] or 'W'); y-=12
    c.setFillColor(INK); c.setFont('Helvetica-Bold',42); c.drawString(M,y,issue); y-=55
    c.setStrokeColor(INK); c.setLineWidth(2); c.line(M,y,W-M,y); y-=22
    c.setFillColor(MUTED); c.setFont('Helvetica-Bold',8); c.drawString(M,y,'A CONTINUACIÓN'); y-=18
    p,hh=wrap_title(c,article_title(a),M,y,W-2*M,27,17); p.drawOn(c,M,y-hh); y-=hh+8
    dek=str(a.get('description') or '').strip()
    if dek:
        p=Paragraph(esc(dek),DEK); _,ph=p.wrap(W-2*M,90); p.drawOn(c,M,y-ph); y-=ph
    draw_footer(c,ed_issue_placeholder(a),n,False); c.showPage()

def section_name(a):return str(a.get('category') or 'SELECCIÓN WEEKLY').upper()
def ed_issue_placeholder(a):return ''

def other_sources(a):
    vals=[]
    for o in a.get('otherSources') or []:
        if isinstance(o,dict): vals.append(o)
    seen=set(); out=[]; lead=str(a.get('source') or '').lower().strip()
    for o in vals:
        s=str(o.get('source') or '').strip(); link=str(o.get('link') or '').strip()
        if not s or s.lower()==lead:continue
        k=(s+'|'+link).lower()
        if k in seen:continue
        seen.add(k); out.append((s,link))
    return out[:5]

def draw_article(c,a,issue,page_no,story_index):
    dark=(story_index%6)==5
    new_page(c,dark)
    source=a.get('source') or 'FUENTE ORIGINAL'; date=str(a.get('published') or '')[:10]
    draw_running(c,source,date,dark)
    ink=DARK_TEXT if dark else INK; muted=colors.HexColor('#b8b4ac') if dark else MUTED
    y=H-M-27; width=W-2*M
    cat=str(a.get('category') or 'OTROS').upper()
    c.setFillColor(ACID if dark else colors.HexColor('#55524c')); c.setFont('Helvetica-Bold',7); c.drawString(M,y,cat); y-=13
    max_title=38 if story_index%6==0 else (32 if story_index%6 in (1,2,3) else 28)
    title_style=style('article_dark_title' if dark else 'article_title',max_title,max_title*.92,'Helvetica-Bold',ink,7); p=Paragraph(esc(article_title(a)),title_style); _,hh=p.wrap(width,210); p.drawOn(c,M,y-hh); y-=hh+3
    dek=str(a.get('description') or '').strip()
    if dek:
        st=DEK_DARK if dark else DEK; p=Paragraph(esc(dek),st); _,ph=p.wrap(width,70); p.drawOn(c,M,y-ph); y-=ph+7
    imgs=article_images(a)
    if imgs:
        ih=180 if story_index%6 in (0,2,5) else 135
        if draw_image(c,imgs[0],M,y-ih,width,ih,contain=False): y-=ih+12
    # A single, continuous column. Never discard blocks; flow to new pages as needed.
    body=BODY_DARK if dark else BODY
    first=True
    for typ,text in story_blocks(a):
        st=SUB_DARK if dark else SUB if typ in {'h1','h2','h3','h4','heading'} else body
        if typ not in {'h1','h2','h3','h4','heading'}: st=body
        p=Paragraph(esc(text).replace('\n','<br/>'),st); _,ph=p.wrap(width,max(40,y-40))
        if ph>y-40:
            draw_footer(c,issue,page_no,dark); c.showPage(); page_no+=1
            new_page(c,dark); draw_running(c,f'{source} · CONTINÚA',date,dark); y=H-M-30
            c.setFillColor(ACID if dark else MUTED); c.setFont('Helvetica-Bold',7); c.drawString(M,y,f'CONTINÚA · HISTORIA {story_index+1:02d}'); y-=14
            p=Paragraph(esc(text).replace('\n','<br/>'),st); _,ph=p.wrap(width,y-35)
            # Paragraphs that exceed a full page are split at sentence/word boundaries.
            if ph>y-35:
                words=text.split(); chunk=[]; remaining=words[:]
                while remaining:
                    lo,hi=1,len(remaining); best=None
                    while lo<=hi:
                        mid=(lo+hi)//2; candidate=' '.join(remaining[:mid]); test=Paragraph(esc(candidate),st); _,th=test.wrap(width,y-35)
                        if th<=y-35: best=(candidate,th,mid); lo=mid+1
                        else: hi=mid-1
                    if not best: best=(' '.join(remaining[:1]),st.fontSize*1.5,1)
                    candidate,th,used=best; Paragraph(esc(candidate),st).wrap(width,y-35)[0] if False else None
                    p2=Paragraph(esc(candidate),st); _,th=p2.wrap(width,y-35); p2.drawOn(c,M,y-th); y-=th+7; remaining=remaining[used:]
                    if remaining:
                        draw_footer(c,issue,page_no,dark); c.showPage(); page_no+=1; new_page(c,dark); draw_running(c,f'{source} · CONTINÚA',date,dark); y=H-M-30
                continue
        p.drawOn(c,M,y-ph); y-=ph+2
        if y<45:
            draw_footer(c,issue,page_no,dark); c.showPage(); page_no+=1; new_page(c,dark); draw_running(c,f'{source} · CONTINÚA',date,dark); y=H-M-30
    # Other sources and original link on final page.
    others=other_sources(a)
    if others:
        if y<95:
            draw_footer(c,issue,page_no,dark); c.showPage(); page_no+=1; new_page(c,dark); draw_running(c,f'{source} · FUENTES',date,dark); y=H-M-30
        c.setFillColor(ACID if dark else INK); c.setFont('Helvetica-Bold',8); c.drawString(M,y,'OTRAS FUENTES'); y-=13
        c.setFillColor(ink); c.setFont('Helvetica-Bold',8)
        for s,link in others:
            c.drawString(M+8,y,f'• {s}'); y-=11
    if a.get('link'):
        c.setFillColor(ACID if dark else INK); c.setFont('Helvetica-Bold',7); c.drawString(M,y-4,'LEER ORIGINAL ↗')
    draw_footer(c,issue,page_no,dark); c.showPage()
    return page_no+1

def draw_short_news(c,shorts,issue,page_no):
    for off in range(0,len(shorts),5):
        batch=shorts[off:off+5]; new_page(c,False); draw_running(c,'WEEKLY · NOTICIAS BREVES','',False)
        y=H-M-28; c.setFillColor(INK); c.setFont('Helvetica-Bold',8); c.drawString(M,y,'NOTICIAS BREVES'); y-=28
        c.setFont('Helvetica-Bold',30); c.drawString(M,y,'LECTURAS RÁPIDAS'); y-=30
        c.setStrokeColor(INK); c.line(M,y,W-M,y); y-=18
        for a in batch:
            c.setFillColor(MUTED); c.setFont('Helvetica-Bold',6.8); c.drawString(M,y,f"{str(a.get('source') or 'FUENTE').upper()} · {str(a.get('published') or '')[:10]}"); y-=10
            p=Paragraph(esc(article_title(a)),style('sh',12.5,13.5,'Helvetica-Bold',INK,3)); _,ph=p.wrap(W-2*M,y-50); p.drawOn(c,M,y-ph); y-=ph+2
            p=Paragraph(esc(a.get('description') or ''),style('sd',8.8,12,'Times-Roman',INK,4)); _,ph=p.wrap(W-2*M,y-45); p.drawOn(c,M,y-ph); y-=ph+3
            c.setStrokeColor(LINE); c.line(M,y,W-M,y); y-=10
        draw_footer(c,issue,page_no,False); c.showPage(); page_no+=1
    return page_no

def draw_closing(c,issue,page_no,count):
    new_page(c,True); c.setFillColor(ACID); c.setFont('Helvetica-Bold',110); c.drawString(M,120,'W')
    c.setFillColor(DARK_TEXT); c.setFont('Helvetica-Bold',8); c.drawString(M,355,'FIN DE LA EDICIÓN');
    c.setFont('Helvetica-Bold',38); c.drawString(M,315,'NOS VEMOS'); c.drawString(M,275,'LA PRÓXIMA SEMANA.')
    c.setFont('Times-Roman',11); c.drawString(M,235,'WEEKLY reúne las fuentes elegidas y las convierte en una revista.');
    c.setFont('Helvetica-Bold',8); c.setFillColor(ACID); c.drawString(M,205,f'{count} HISTORIAS · EDICIÓN #{issue}')
    draw_footer(c,issue,page_no,True); c.showPage()

def main():
    arts_data=load(ARTICLES,{}); ed=load(EDITORIAL,{})
    if not ed.get('locked'): raise SystemExit('No hay edición cerrada; PDF omitido.')
    issue=str(ed.get('issueNumber','?')); OUT_DIR.mkdir(parents=True,exist_ok=True); out=OUT_DIR/f'issue-{issue}.pdf'
    arts=arts_data.get('articles',[]) if isinstance(arts_data,dict) else []
    ids=ed.get('selected_ids') or []
    selected=[arts[i] for i in ids if isinstance(i,int) and 0<=i<len(arts)]
    full=[a for a in selected if a.get('contentStatus')!='short']; shorts=[a for a in selected if a.get('contentStatus')=='short']
    c=canvas.Canvas(str(out),pagesize=A4); c.setTitle(f'WEEKLY #{issue}'); c.setAuthor('WEEKLY')
    draw_cover(c,ed,selected,1); page_no=2
    draw_editorial(c,ed,page_no); page_no+=1
    last_section=None; section_no=0
    for idx,a in enumerate(full):
        sec=section_name(a)
        if sec!=last_section:
            section_no+=1; draw_section(c,a,page_no,section_no); page_no+=1; last_section=sec
        page_no=draw_article(c,a,issue,page_no,idx)
    if shorts: page_no=draw_short_news(c,shorts,issue,page_no)
    draw_closing(c,issue,page_no,len(selected)); c.save()
    idx=load(INDEX,{'issues':[]}); issues=idx.get('issues',[]) if isinstance(idx,dict) else []
    entry={'number':issue,'start':(ed.get('issueWindow') or {}).get('start',''),'end':(ed.get('issueWindow') or {}).get('end',''),'stories':len(selected),'locked':True,'cover':ed.get('coverImage') or 'assets/weekly-cover-fallback.svg','pdf':str(out).replace('\\','/'),'file':f'data/issues/issue-{issue}.json' if (OUT_DIR/f'issue-{issue}.json').exists() else ''}
    issues=[x for x in issues if str(x.get('number'))!=issue]; issues.append(entry); issues.sort(key=lambda x:int(x.get('number') or 0),reverse=True)
    INDEX.write_text(json.dumps({'issues':issues},ensure_ascii=False,indent=2),encoding='utf-8')
    print(out)

if __name__=='__main__':main()
