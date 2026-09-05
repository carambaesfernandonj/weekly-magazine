import json, re, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

FEEDS_FILE="data/feeds.json"
OUT_FILE="data/articles.json"

def clean(s):
    if not s: return ""
    s=re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"\s+"," ",unescape(s)).strip()

def get_text(el, names):
    for name in names:
        x=el.find(name)
        if x is not None and x.text:
            return clean(x.text)
    return ""

def parse_date(value):
    if not value: return ""
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except Exception:
        return value

def parse_feed(feed):
    req=urllib.request.Request(feed["url"],headers={"User-Agent":"WEEKLY/0.2 RSS reader"})
    with urllib.request.urlopen(req,timeout=20) as r:
        raw=r.read()
    root=ET.fromstring(raw)
    out=[]
    # RSS 2.0
    for item in root.findall(".//item"):
        title=get_text(item,["title"])
        link=get_text(item,["link"])
        desc=get_text(item,["description","content"])
        pub=get_text(item,["pubDate","date"])
        guid=get_text(item,["guid"]) or link
        if title and link:
            out.append({"id":guid,"title":title,"link":link,"description":desc,
                        "published":parse_date(pub),"source":feed["name"],
                        "category":feed.get("category","Other")})
    # Atom (The Verge and others)
    ns={"atom":"http://www.w3.org/2005/Atom"}
    for e in root.findall(".//atom:entry",ns):
        title=get_text(e,["{http://www.w3.org/2005/Atom}title"])
        link_el=e.find("atom:link",ns)
        link=link_el.get("href","") if link_el is not None else ""
        desc=get_text(e,["{http://www.w3.org/2005/Atom}summary","{http://www.w3.org/2005/Atom}content"])
        pub=get_text(e,["{http://www.w3.org/2005/Atom}published","{http://www.w3.org/2005/Atom}updated"])
        guid=get_text(e,["{http://www.w3.org/2005/Atom}id"]) or link
        if title and link:
            out.append({"id":guid,"title":title,"link":link,"description":desc,
                        "published":parse_date(pub),"source":feed["name"],
                        "category":feed.get("category","Other")})
    return out

with open(FEEDS_FILE,encoding="utf-8") as f:
    feeds=json.load(f)["feeds"]

articles=[]
errors=[]
for feed in feeds:
    if not feed.get("enabled",True): continue
    try:
        articles.extend(parse_feed(feed))
    except Exception as e:
        errors.append({"source":feed["name"],"error":str(e)})

# Deduplicate by URL/id, then keep newest 300.
seen=set(); unique=[]
for a in sorted(articles,key=lambda x:x.get("published",""),reverse=True):
    key=a["link"] or a["id"]
    if key in seen: continue
    seen.add(key); unique.append(a)
unique=unique[:300]

payload={"updatedAt":datetime.now(timezone.utc).isoformat(),"articles":unique,"errors":errors}
with open(OUT_FILE,"w",encoding="utf-8") as f:
    json.dump(payload,f,ensure_ascii=False,indent=2)
print(f"Fetched {len(unique)} articles from {len(feeds)} feeds; errors={len(errors)}")
