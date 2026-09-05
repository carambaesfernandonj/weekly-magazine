import json, os, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urljoin
from html.parser import HTMLParser

FEEDS_FILE="data/feeds.json"
OUT_FILE="data/articles.json"
SUPABASE_URL=os.environ.get("SUPABASE_URL","").rstrip("/")
SUPABASE_SECRET_KEY=os.environ.get("SUPABASE_SECRET_KEY","")
MAX_PER_FEED=100
MAX_TOTAL=300
ENRICH_LIMIT=24

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1=[]; self.h2=[]; self.og_image=""; self._tag=None; self._buf=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        tag=tag.lower()
        if tag in ("h1","h2"):
            self._tag=tag; self._buf=[]
        if tag=="meta":
            key=(a.get("property") or a.get("name") or "").lower()
            if key in ("og:image","twitter:image") and a.get("content") and not self.og_image:
                self.og_image=a["content"]
    def handle_data(self, data):
        if self._tag: self._buf.append(data)
    def handle_endtag(self, tag):
        tag=tag.lower()
        if tag==self._tag:
            text=clean(" ".join(self._buf))
            if text:
                target=self.h1 if tag=="h1" else self.h2
                if text not in target and len(target)<3: target.append(text)
            self._tag=None; self._buf=[]

def load_feeds():
    if SUPABASE_URL and SUPABASE_SECRET_KEY:
        url=SUPABASE_URL+"/rest/v1/sources?select=id,name,url,category,enabled&enabled=eq.true&order=created_at.asc"
        req=urllib.request.Request(url,headers={"apikey":SUPABASE_SECRET_KEY,"User-Agent":"WEEKLY/0.7"})
        with urllib.request.urlopen(req,timeout=20) as r: rows=json.loads(r.read().decode("utf-8"))
        if rows:
            print(f"Loaded {len(rows)} enabled feeds from Supabase")
            return rows
        print("Supabase returned no enabled feeds; falling back to data/feeds.json")
    with open(FEEDS_FILE,encoding="utf-8") as f: return json.load(f)["feeds"]

def clean(s):
    if not s: return ""
    s=re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>"," ",s,flags=re.I)
    s=re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"\s+"," ",unescape(s)).strip()

def text(el,names):
    for name in names:
        x=el.find(name)
        if x is not None and x.text: return clean(x.text)
    return ""

def date_iso(v):
    if not v: return ""
    try: return parsedate_to_datetime(v).astimezone(timezone.utc).isoformat()
    except Exception: return v

def image_from_item(el,base=""):
    for x in el.findall(".//*"):
        tag=x.tag.split("}")[-1].lower()
        if tag in ("content","thumbnail","enclosure","image"):
            url=x.attrib.get("url") or x.attrib.get("href"); typ=x.attrib.get("type","")
            if url and ("image" in typ or tag in ("thumbnail","content","image")): return urljoin(base,url)
    desc=text(el,["description","summary","{http://www.w3.org/2005/Atom}summary"])
    m=re.search(r'<img[^>]+src=["\']([^"\']+)',desc,re.I)
    return urljoin(base,m.group(1)) if m else ""

def parse(feed):
    req=urllib.request.Request(feed["url"],headers={"User-Agent":"WEEKLY/0.7 (+personal RSS reader)"})
    with urllib.request.urlopen(req,timeout=25) as r: raw=r.read(); final_url=r.geturl()
    root=ET.fromstring(raw); out=[]
    for item in root.findall(".//item")[:MAX_PER_FEED]:
        title=text(item,["title"]); link=text(item,["link"])
        if not link:
            for l in item.findall("link"):
                if l.attrib.get("href"): link=l.attrib["href"]; break
        if title and link:
            out.append({"id":text(item,["guid"]) or link,"title":title,"link":link,
                "description":text(item,["description","content:encoded","summary"]),
                "published":date_iso(text(item,["pubDate","published","updated","dc:date"])),
                "source":feed["name"],"category":feed.get("category","Other"),"image":image_from_item(item,final_url)})
    ns={"a":"http://www.w3.org/2005/Atom"}
    for e in root.findall(".//a:entry",ns)[:MAX_PER_FEED]:
        title=text(e,["{http://www.w3.org/2005/Atom}title"]); le=e.find("a:link",ns); link=le.attrib.get("href","") if le is not None else ""
        if title and link:
            out.append({"id":text(e,["{http://www.w3.org/2005/Atom}id"]) or link,"title":title,"link":link,
                "description":text(e,["{http://www.w3.org/2005/Atom}summary","{http://www.w3.org/2005/Atom}content"]),
                "published":date_iso(text(e,["{http://www.w3.org/2005/Atom}published","{http://www.w3.org/2005/Atom}updated"])),
                "source":feed["name"],"category":feed.get("category","Other"),"image":image_from_item(e,final_url)})
    return out

STOP=set("the a an and or of to in on for with from by is are was were this that how why what your you new news more into about after as at it its".split())
def tokens(title):
    words=re.findall(r"[a-zA-ZÀ-ÿ0-9]{3,}",title.lower()); return set(w for w in words if w not in STOP)
def score(a,all_articles):
    t=tokens(a["title"]); related=0
    for b in all_articles:
        if b is a: continue
        u=tokens(b["title"])
        if t and u and len(t&u)/max(1,len(t|u))>=.38: related+=1
    rec=0
    try:
        dt=datetime.fromisoformat(a["published"].replace("Z","+00:00")); age=(datetime.now(timezone.utc)-dt).total_seconds()/86400; rec=max(0,7-age)
    except Exception: pass
    return min(100,55+min(25,related*5)+min(15,rec*2)+(5 if a.get("image") else 0))

def enrich_article(a):
    """Fetch the article page once to capture the main image and H1/H2s. Failure is non-fatal."""
    try:
        req=urllib.request.Request(a["link"],headers={"User-Agent":"Mozilla/5.0 (compatible; WEEKLY/0.7; +personal reader)"})
        with urllib.request.urlopen(req,timeout=10) as r:
            raw=r.read(700000); final=r.geturl()
        html=raw.decode("utf-8",errors="replace")
        p=PageParser(); p.feed(html)
        if p.og_image: a["image"]=urljoin(final,p.og_image)
        a["headings"]={"h1":p.h1[:2],"h2":p.h2[:4]}
    except Exception as e:
        a.setdefault("headings",{"h1":[],"h2":[]}); a["enrichError"]=str(e)[:180]
    return a

TAG_RULES={
    "GAMING":[r"\bgame(?:s)?\b",r"gaming",r"nintendo",r"zelda",r"xbox",r"playstation",r"tomb raider",r"psychonauts",r"double fine",r"gamescom",r"dracula",r"halloween"],
    "NINTENDO":[r"nintendo",r"zelda",r"switch"],
    "XBOX":[r"xbox",r"microsoft"],
    "PLAYSTATION":[r"playstation",r"ps5",r"sony"],
    "HARDWARE":[r"iphone",r"ipad",r"mac",r"speaker",r"console",r"device",r"hardware",r"microphone",r"phone",r"watch"],
    "APPLE":[r"apple",r"iphone",r"ipad",r"mac"],
    "AI":[r"\bai\b",r"artificial intelligence",r"openai",r"agent(?:s)?\b",r"machine learning"],
    "SCIENCE":[r"scientist",r"science",r"research",r"caterpillar",r"microphone",r"study",r"researchers"],
    "SPACE":[r"space",r"nasa",r"rocket",r"satellite"],
    "AUTOMOTIVE":[r"tesla",r"cybercab",r"vehicle",r"car(?:s)?\b",r"automotive"],
    "BUSINESS":[r"business",r"sales",r"sold",r"million",r"deal",r"discount",r"promo",r"coupon"],
    "DEALS":[r"deal(?:s)?\b",r"discount",r"promo",r"coupon",r"save ",r"off\b"],
    "HORROR":[r"horror",r"halloween",r"dracula",r"vampire",r"blood",r"terror"],
    "CULTURE":[r"culture",r"watch world",r"fashion",r"movie",r"film",r"music"],
    "SECURITY":[r"hack(?:ed|ing)?",r"security",r"dark web",r"data breach",r"military",r"license(?:s)?"],
    "TECHNOLOGY":[r"technology",r"tech",r"device",r"digital",r"internet",r"online"],
}

def make_tags(a):
    hay=" ".join([a.get("title",""),a.get("description","")]).lower()
    tags=[]
    cat=(a.get("category") or "Other").upper()
    if cat not in ("OTHER",""): tags.append(cat)
    for tag,patterns in TAG_RULES.items():
        if tag in tags: continue
        if any(re.search(p,hay,re.I) for p in patterns): tags.append(tag)
    return tags[:7]

feeds=load_feeds(); articles=[]; errors=[]
for feed in feeds:
    if not feed.get("enabled",True): continue
    try: articles.extend(parse(feed))
    except Exception as e: errors.append({"source":feed["name"],"error":str(e)})
seen=set(); unique=[]
for a in sorted(articles,key=lambda x:x.get("published",""),reverse=True):
    key=a["link"] or a["id"]
    if key not in seen: seen.add(key); unique.append(a)
unique=unique[:MAX_TOTAL]
for a in unique:
    a["tags"]=make_tags(a)
    a["editorialScore"]=round(score(a,unique))
clusters=[]; unused=set(range(len(unique)))
while unused:
    i=unused.pop(); group=[i]; ti=tokens(unique[i]["title"])
    for j in list(unused):
        tj=tokens(unique[j]["title"]); sim=len(ti&tj)/max(1,len(ti|tj))
        if sim>=.38: group.append(j); unused.remove(j)
    best=max(group,key=lambda k:unique[k]["editorialScore"]); clusters.append({"lead":best,"articleIds":group})
leads=sorted((unique[c["lead"]] for c in clusters),key=lambda a:a["editorialScore"],reverse=True)
selected=[]; counts={}
for a in leads:
    cat=a["category"]
    if counts.get(cat,0)>=8: continue
    selected.append(a); counts[cat]=counts.get(cat,0)+1
    if len(selected)>=24: break
for a in selected: a["selected"]=True
for a in unique: a.setdefault("selected",False)

# Enrich only the stories that can actually enter this week's magazine: cheap, bounded, non-AI.
for n,a in enumerate(selected[:ENRICH_LIMIT],1):
    print(f"Enriching article page {n}/{min(ENRICH_LIMIT,len(selected))}: {a['title'][:70]}")
    enrich_article(a)

payload={"updatedAt":datetime.now(timezone.utc).isoformat(),"articles":unique,"selected":selected,"clusters":clusters,"errors":errors,
         "editor":{"version":"0.7-zero-cost","note":"WEEKLY uses RSS metadata, source images and article headings. No AI credits are required."}}
with open(OUT_FILE,"w",encoding="utf-8") as f: json.dump(payload,f,ensure_ascii=False,indent=2)
print(f"Fetched {len(unique)} articles; {len(clusters)} clusters; {len(selected)} selected; enriched={min(ENRICH_LIMIT,len(selected))}; errors={len(errors)}")
