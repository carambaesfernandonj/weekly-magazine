import json, os, urllib.request
from datetime import datetime, timezone

ARTICLES="data/articles.json"
OUT="data/editorial.json"
API="https://api.openai.com/v1/responses"

def call_openai(articles):
    key=os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured in GitHub Secrets")

    candidates=[]
    for i,a in enumerate(articles[:80]):
        candidates.append({
            "id": i,
            "title": a.get("title",""),
            "source": a.get("source",""),
            "category": a.get("category","Other"),
            "description": a.get("description","")[:700],
            "published": a.get("published",""),
            "link": a.get("link",""),
            "image": a.get("image","")
        })

    schema={
      "type":"object",
      "additionalProperties":False,
      "properties":{
        "cover_story":{"type":"integer"},
        "selected_ids":{"type":"array","items":{"type":"integer"}},
        "stories":[
        ],
        "sections":{"type":"array","items":{
          "type":"object","additionalProperties":False,
          "properties":{
            "name":{"type":"string"},
            "ids":{"type":"array","items":{"type":"integer"}}
          },
          "required":["name","ids"]
        }},
        "editor_note":{"type":"string"}
      },
      "required":["cover_story","selected_ids","sections","editor_note"]
    }
    # Keep schema strict-compatible; stories are generated client-side from article data.
    payload={
      "model":"gpt-5.6-luna",
      "store":False,
      "instructions":(
        "You are the editor-in-chief of WEEKLY, a personal weekly magazine about technology, "
        "video games, internet culture and adjacent topics. Select the most interesting and "
        "useful stories from the supplied RSS candidates. Merge obvious duplicates conceptually "
        "by selecting only the strongest source. Prefer diversity across sources and categories. "
        "Pick 12-24 stories. Pick exactly one cover story. Do not invent facts. Use only the supplied "
        "candidate IDs. Create 4-6 sections with concise names. Return only the requested JSON."
      ),
      "input":json.dumps(candidates,ensure_ascii=False),
      "text":{"format":{"type":"json_schema","name":"weekly_editorial","strict":True,"schema":schema}}
    }
    req=urllib.request.Request(API,data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
        method="POST")
    with urllib.request.urlopen(req,timeout=90) as r:
        data=json.loads(r.read().decode("utf-8"))
    return json.loads(data["output_text"])

with open(ARTICLES,encoding="utf-8") as f: data=json.load(f)
articles=data.get("articles",[])
if not articles:
    raise RuntimeError("No articles available. Run the RSS fetch first.")

try:
    editorial=call_openai(articles)
    valid=set(range(len(articles)))
    editorial["selected_ids"]=[i for i in editorial.get("selected_ids",[]) if i in valid][:24]
    if editorial.get("cover_story") not in valid:
        editorial["cover_story"]=editorial["selected_ids"][0] if editorial["selected_ids"] else 0
    editorial["generatedAt"]=datetime.now(timezone.utc).isoformat()
    editorial["model"]="gpt-5.6-luna"
    editorial["status"]="ai"
except Exception as e:
    # Never destroy a working issue if the API is unavailable.
    fallback=[i for i,a in enumerate(articles) if a.get("selected")][:24]
    editorial={
      "cover_story":fallback[0] if fallback else 0,
      "selected_ids":fallback,
      "sections":[{"name":"WEEKLY PICKS","ids":fallback}],
      "editor_note":"AI editor unavailable; using the automatic fallback selection.",
      "generatedAt":datetime.now(timezone.utc).isoformat(),
      "model":"fallback",
      "status":"fallback",
      "error":str(e)
    }

with open(OUT,"w",encoding="utf-8") as f:
    json.dump(editorial,f,ensure_ascii=False,indent=2)
print("Editorial issue:", editorial.get("status"), "selected:", len(editorial.get("selected_ids",[])))
