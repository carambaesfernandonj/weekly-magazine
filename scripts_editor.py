import json, os
from datetime import datetime, timezone

ARTICLES="data/articles.json"
OUT="data/editorial.json"
# V0.7 is intentionally zero-cost by default. AI can be re-enabled later with ENABLE_AI=true.
ENABLE_AI=os.environ.get("ENABLE_AI","false").lower()=="true"
MODEL="gpt-5.6-luna"
EDITORIAL_PROFILE={"name":"Fernando Mode","voice":"intelligent, curious, informal and editorial","humor":"dry and occasional; never force jokes","attitude":"opinionated but fair, skeptical of hype, interested in weird connections","writing":"strong headlines, short paragraphs, clear explanations, occasional punchlines","rule":"inform first, entertain second; never invent facts"}

def fallback_editorial(articles):
    fallback=[i for i,a in enumerate(articles) if a.get("selected")][:24]
    if len(fallback)<12: fallback=list(range(min(16,len(articles))))
    stories=[]
    for i in fallback:
        a=articles[i]; desc=(a.get("description") or "").strip()
        if len(desc)>900: desc=desc[:897].rstrip()+"..."
        h=a.get("headings") or {}; h1=h.get("h1") or []; h2=h.get("h2") or []
        stories.append({"article_id":i,"headline":a.get("title","Untitled"),"dek":desc or "Historia publicada por la fuente original.","summary":desc or "Consulta la fuente original para leer la historia completa.","why_it_matters":"WEEKLY presenta el material original de la fuente, sin generar ni inventar contenido adicional.","key_points":([f"H1: {h1[0]}"] if h1 else [])+([f"H2: {x}" for x in h2[:3]]) or [f"Fuente: {a.get('source','Unknown')}"],"headings":{"h1":h1,"h2":h2}})
    return {"cover_story":fallback[0] if fallback else 0,"selected_ids":fallback,"stories":stories,
            "sections":[{"name":"WEEKLY PICKS","ids":fallback}],
            "editor_note":"Edición automática sin IA: WEEKLY utiliza títulos, imágenes, descripciones y headings de las fuentes originales.",
            "generatedAt":datetime.now(timezone.utc).isoformat(),"model":"zero-cost","status":"rss","editorial_profile":EDITORIAL_PROFILE}

with open(ARTICLES,encoding="utf-8") as f: data=json.load(f)
articles=data.get("articles",[])
if not articles: raise RuntimeError("No articles available. Run the RSS fetch first.")

# V0.7 deliberately avoids any OpenAI call. This keeps the weekly build usable with zero API balance.
editorial=fallback_editorial(articles)

with open(OUT,"w",encoding="utf-8") as f: json.dump(editorial,f,ensure_ascii=False,indent=2)
print("Editorial issue:",editorial.get("status"),"selected:",len(editorial.get("selected_ids",[])))
