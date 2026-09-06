import json, os, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
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
ENRICH_LIMIT=120

class PageParser(HTMLParser):
    """Extract the main article image, headings and readable text blocks."""
    SKIP={"script","style","nav","header","footer","aside","form","noscript","svg"}
    BLOCKS={"p","h1","h2","h3","h4","blockquote","li"}
    SIGNALS=("article","post","entry","content","story","body","main")
    def __init__(self):
        super().__init__()
        self.h1=[]; self.h2=[]; self.og_image=""; self.images=[]
        self.blocks=[]; self._stack=[]; self._tag=None; self._buf=[]; self._score=0
    def handle_starttag(self, tag, attrs):
        tag=tag.lower(); a=dict(attrs)
        if tag=="meta":
            key=(a.get("property") or a.get("name") or "").lower()
            if key in ("og:image","twitter:image") and a.get("content") and not self.og_image:
                self.og_image=a["content"]
        # Capture article-body images as well as the OpenGraph hero image.
        if tag=="img":
            src=(a.get("src") or a.get("data-src") or a.get("data-lazy-src") or a.get("data-original") or "").strip()
            if not src and a.get("srcset"):
                src=a.get("srcset").split(",")[0].strip().split(" ")[0]
            if src:
                alt=(a.get("alt") or a.get("title") or "").strip()
                self.images.append({"url":src,"caption":alt})

        cls=f"{a.get('id','')} {a.get('class','')}".lower()
        signal=any(x in cls for x in self.SIGNALS)
        delta=0
        if tag in ("article","main"): delta+=4
        if signal: delta+=2
        if tag in self.SKIP: delta-=100
        self._stack.append((tag, self._score, tag in self.SKIP or any(x[2] for x in self._stack)))
        if self._stack[-1][2]: return
        self._score+=delta
        if tag in self.BLOCKS:
            self._tag=tag; self._buf=[]; self._block_score=self._score
    def handle_data(self, data):
        if self._tag and data.strip(): self._buf.append(data)
    def handle_endtag(self, tag):
        tag=tag.lower()
        if tag==self._tag:
            text=clean(" ".join(self._buf))
            if text:
                if tag=="h1" and len(self.h1)<3 and text not in self.h1: self.h1.append(text)
                elif tag=="h2" and len(self.h2)<6 and text not in self.h2: self.h2.append(text)
                self.blocks.append({"type":tag,"text":text,"score":self._block_score})
            self._tag=None; self._buf=[]
        if self._stack:
            _,old_score,was_skip=self._stack.pop()
            self._score=old_score

    def readable_blocks(self):
        if not self.blocks: return []
        best=max(b["score"] for b in self.blocks)
        # Prefer blocks inside the strongest article/content container, while allowing
        # neighboring blocks at nearly the same depth.
        chosen=[b for b in self.blocks if b["score"]>=max(1,best-1)]
        if len(chosen)<3: chosen=self.blocks
        out=[]; seen=set()
        for b in chosen:
            t=b["text"]
            if len(t)<25 and b["type"]=="p": continue
            if t.lower() in seen: continue
            seen.add(t.lower()); out.append({"type":b["type"],"text":t})
        # Keep the generated data reasonably small while retaining enough text for several magazine pages.
        total=0; trimmed=[]
        for b in out:
            if total>=30000: break
            t=b["text"]
            remaining=30000-total
            if len(t)>remaining: t=t[:remaining].rsplit(" ",1)[0].strip()
            if not t: break
            trimmed.append({"type":b["type"],"text":t}); total+=len(t)+2
        return trimmed

def load_feeds():
    # Supabase is the source of truth for the sources managed by the app.
    # feeds.json is only a generated mirror / local fallback.
    if SUPABASE_URL and SUPABASE_SECRET_KEY:
        url=SUPABASE_URL+"/rest/v1/sources?select=id,name,url,category,enabled&enabled=eq.true&order=created_at.asc"
        req=urllib.request.Request(url,headers={
            "apikey":SUPABASE_SECRET_KEY,
            "Authorization":"Bearer "+SUPABASE_SECRET_KEY,
            "User-Agent":"WEEKLY/0.8.4"
        })
        with urllib.request.urlopen(req,timeout=20) as r:
            rows=json.loads(r.read().decode("utf-8"))
        rows=[r for r in rows if r.get("enabled",True) and r.get("url")]
        print(f"Loaded {len(rows)} enabled feeds from Supabase")
        os.makedirs(os.path.dirname(FEEDS_FILE),exist_ok=True)
        with open(FEEDS_FILE,"w",encoding="utf-8") as f:
            json.dump({"updatedAt":datetime.now(timezone.utc).isoformat(),"feeds":rows},f,ensure_ascii=False,indent=2)
        return rows
    if SUPABASE_URL or SUPABASE_SECRET_KEY:
        raise RuntimeError("Supabase configuration is incomplete. Set both SUPABASE_URL and SUPABASE_SECRET_KEY.")
    print("WARNING: Supabase credentials are not configured; using data/feeds.json as local fallback.")
    with open(FEEDS_FILE,encoding="utf-8") as f:
        return json.load(f)["feeds"]

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

def parse_published_datetime(value):
    """Return a timezone-aware UTC datetime when an article date is usable."""
    if not value: return None
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        try:
            dt=parsedate_to_datetime(value)
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

def current_editorial_window(now=None):
    """Return the most recently completed Sunday→Saturday editorial week.

    WEEKLY is generated on Sunday (or later) and the new issue covers the
    previous Sunday at 00:00 through the following Sunday at 00:00.
    """
    now=now or datetime.now(timezone.utc)
    today=now.date()
    # Python weekday(): Monday=0 ... Sunday=6.
    days_since_sunday=(today.weekday()+1) % 7
    week_end=datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    if days_since_sunday:
        week_end -= timedelta(days=days_since_sunday)
    week_start=week_end-timedelta(days=7)
    return week_start, week_end

def is_in_editorial_window(article, start, end):
    published=parse_published_datetime(article.get("published",""))
    if published is None:
        return False
    return start <= published < end

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
    req=urllib.request.Request(feed["url"],headers={"User-Agent":"WEEKLY/0.8.3 (+personal RSS reader)"})
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
        req=urllib.request.Request(a["link"],headers={"User-Agent":"Mozilla/5.0 (compatible; WEEKLY/0.8.3; +personal reader)"})
        with urllib.request.urlopen(req,timeout=10) as r:
            raw=r.read(700000); final=r.geturl()
        html=raw.decode("utf-8",errors="replace")
        p=PageParser(); p.feed(html)
        if p.og_image: a["image"]=urljoin(final,p.og_image)
        # Keep a small, useful gallery: hero image first, then unique body images.
        image_candidates=[]; seen_images=set()
        if a.get("image"):
            image_candidates.append({"url":a["image"],"caption":""}); seen_images.add(a["image"])
        for item in p.images:
            u=urljoin(final,item.get("url","")).strip()
            low=u.lower()
            if not u or u in seen_images: continue
            # Conservative noise filter for logos, avatars, trackers and UI assets.
            if any(x in low for x in ("favicon","avatar","gravatar","sprite","tracking","pixel","placeholder","logo-small","social-icon","share-icon")): continue
            if re.search(r"(?:1x1|spacer|blank)\.(?:gif|png|jpg|jpeg|webp)(?:$|[?#])",low): continue
            seen_images.add(u); image_candidates.append({"url":u,"caption":item.get("caption","")})
            if len(image_candidates)>=6: break
        a["images"]=image_candidates[:6]
        blocks=p.readable_blocks()
        a["headings"]={"h1":p.h1[:2],"h2":p.h2[:4]}
        a["contentBlocks"]=blocks
        a["contentText"]="\n\n".join(b["text"] for b in blocks if b["type"] in ("p","blockquote"))
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
# Only the most recently completed Sunday→Saturday editorial week is eligible
# for the magazine. Running the workflow on Sunday therefore closes the
# previous week and prevents older RSS entries from leaking into the issue.
issue_start, issue_end=current_editorial_window()
window_articles=[a for a in articles if is_in_editorial_window(a,issue_start,issue_end)]
excluded_old=len(articles)-len(window_articles)
print(f"Editorial window: {issue_start.date()} → {issue_end.date()} (end exclusive); eligible={len(window_articles)}; excluded_outside_window={excluded_old}")

seen=set(); unique=[]
for a in sorted(window_articles,key=lambda x:x.get("published",""),reverse=True):
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

# Build a diverse weekly shortlist. The old selector walked the global ranking,
# which meant one prolific feed (for example IGN) could fill almost the entire
# 24-story issue. Round-robin the feeds first, then fill remaining slots by score.
source_buckets={}
for a in leads:
    key=str(a.get("source") or "Unknown").strip() or "Unknown"
    source_buckets.setdefault(key,[]).append(a)
for key in source_buckets:
    source_buckets[key].sort(key=lambda x:x.get("editorialScore",0),reverse=True)

selected=[]; selected_keys=set(); source_counts={}; category_counts={}
source_order=sorted(source_buckets, key=lambda k: source_buckets[k][0].get("editorialScore",0), reverse=True)

# First pass: give every feed a chance to contribute, then make a second pass
# for feeds with more stories. This is deliberately source-aware rather than
# category-only.
while len(selected)<24:
    progressed=False
    for source_name in source_order:
        bucket=source_buckets[source_name]
        if not bucket: continue
        a=bucket.pop(0); key=a.get("link") or a.get("id")
        if key in selected_keys: continue
        # Avoid one source swallowing the issue while still allowing large feeds.
        if source_counts.get(source_name,0)>=4: continue
        cat=a.get("category") or "Other"
        if category_counts.get(cat,0)>=8: continue
        selected.append(a); selected_keys.add(key)
        source_counts[source_name]=source_counts.get(source_name,0)+1
        category_counts[cat]=category_counts.get(cat,0)+1
        progressed=True
        if len(selected)>=24: break
    if not progressed: break

# If diversity constraints left empty slots, fill them with the best remaining
# stories while keeping the 4-per-source cap.
if len(selected)<24:
    remaining=sorted(
        (a for a in unique if (a.get("link") or a.get("id")) not in selected_keys),
        key=lambda x:x.get("editorialScore",0), reverse=True
    )
    for a in remaining:
        source_name=str(a.get("source") or "Unknown").strip() or "Unknown"
        cat=a.get("category") or "Other"
        if source_counts.get(source_name,0)>=4 or category_counts.get(cat,0)>=8: continue
        selected.append(a); selected_keys.add(a.get("link") or a.get("id"))
        source_counts[source_name]=source_counts.get(source_name,0)+1
        category_counts[cat]=category_counts.get(cat,0)+1
        if len(selected)>=24: break
for a in selected: a["selected"]=True
for a in unique: a.setdefault("selected",False)

# Enrich only the stories that can actually enter this week's magazine: cheap, bounded, non-AI.
for n,a in enumerate(selected[:ENRICH_LIMIT],1):
    print(f"Enriching article page {n}/{min(ENRICH_LIMIT,len(selected))}: {a['title'][:70]}")
    enrich_article(a)

payload={"updatedAt":datetime.now(timezone.utc).isoformat(),
         "issueWindow":{"start":issue_start.date().isoformat(),"end":issue_end.date().isoformat(),"timezone":"UTC","endExclusive":True},
         "articles":unique,"selected":selected,"clusters":clusters,"errors":errors,
         "editor":{"version":"0.9.1-week-window","note":"WEEKLY uses only articles published in the most recently completed Sunday→Saturday editorial window. No AI credits are required for the feed fetch, filtering or clustering."}}
with open(OUT_FILE,"w",encoding="utf-8") as f: json.dump(payload,f,ensure_ascii=False,indent=2)
print(f"Fetched {len(unique)} articles; {len(clusters)} clusters; {len(selected)} selected; sources_in_issue={len(set(a.get('source') for a in selected))}; enriched={min(ENRICH_LIMIT,len(selected))}; errors={len(errors)}")

if errors:
    print("")
    print("===== RSS FETCH ERRORS =====")
    for err in errors:
        print(f"[{err['source']}] {err['error']}")
    print("============================")
