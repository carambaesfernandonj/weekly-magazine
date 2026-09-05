import json, os, urllib.request
from datetime import datetime, timezone

ARTICLES = "data/articles.json"
OUT = "data/editorial.json"
API = "https://api.openai.com/v1/responses"
MODEL = "gpt-5.6-luna"

# Personal editorial DNA for the private edition.
EDITORIAL_PROFILE = {
    "name": "Fernando Mode",
    "voice": "intelligent, curious, informal and editorial",
    "humor": "dry and occasional; never force jokes",
    "attitude": "opinionated but fair, skeptical of hype, interested in weird connections",
    "writing": "strong headlines, short paragraphs, clear explanations, occasional punchlines",
    "rule": "inform first, entertain second; never invent facts"
}


def call_openai(articles):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured in GitHub Secrets")

    candidates = []
    for i, a in enumerate(articles[:80]):
        candidates.append({
            "id": i,
            "title": a.get("title", ""),
            "source": a.get("source", ""),
            "category": a.get("category", "Other"),
            "description": a.get("description", "")[:900],
            "published": a.get("published", ""),
            "image": a.get("image", "")
        })

    story_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "article_id": {"type": "integer"},
            "headline": {"type": "string"},
            "dek": {"type": "string"},
            "summary": {"type": "string"},
            "why_it_matters": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4}
        },
        "required": ["article_id", "headline", "dek", "summary", "why_it_matters", "key_points"]
    }

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "cover_story": {"type": "integer"},
            "selected_ids": {"type": "array", "items": {"type": "integer"}, "minItems": 12, "maxItems": 24},
            "stories": {"type": "array", "items": story_schema, "minItems": 12, "maxItems": 24},
            "sections": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "ids": {"type": "array", "items": {"type": "integer"}}
                },
                "required": ["name", "ids"]
            }, "minItems": 3, "maxItems": 6},
            "editor_note": {"type": "string"}
        },
        "required": ["cover_story", "selected_ids", "stories", "sections", "editor_note"]
    }

    instructions = f"""
You are the editor-in-chief of WEEKLY, a personal weekly magazine about technology,
video games, internet culture, design and adjacent topics.

Your job is NOT to reproduce source articles. Create original editorial copy based ONLY
on the supplied RSS metadata and descriptions. Never invent facts, quotes, numbers,
claims, events or details that are not supported by the supplied material.

Editorial personality:
{json.dumps(EDITORIAL_PROFILE, ensure_ascii=False)}

Select 12-24 of the strongest stories. Prefer variety across categories and sources,
and avoid obvious duplicates by choosing the strongest candidate. Pick exactly one cover story.
For EVERY selected story, create a compact original editorial treatment:
- headline: punchy magazine headline, not clickbait
- dek: 1-2 sentence standfirst
- summary: 2-4 sentences explaining what happened
- why_it_matters: 2-4 sentences explaining context/significance without inventing facts
- key_points: 2-4 short factual takeaways grounded in the supplied candidate

Create 3-6 concise magazine sections and an editor's note connecting the week's themes.
Use only candidate IDs. Return only the requested JSON.
"""

    payload = {
        "model": MODEL,
        "store": False,
        "instructions": instructions,
        "input": json.dumps(candidates, ensure_ascii=False),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "weekly_editorial",
                "strict": True,
                "schema": schema
            }
        }
    }

    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI HTTP {e.code}: {body[:1200]}") from e

    if not data.get("output_text"):
        raise RuntimeError("OpenAI returned no output_text")
    return json.loads(data["output_text"])


def fallback_editorial(articles, error):
    fallback = [i for i, a in enumerate(articles) if a.get("selected")][:24]
    if len(fallback) < 12:
        fallback = list(range(min(16, len(articles))))
    stories = []
    for i in fallback:
        a = articles[i]
        desc = (a.get("description") or "").strip()
        if len(desc) > 700:
            desc = desc[:697].rstrip() + "..."
        stories.append({
            "article_id": i,
            "headline": a.get("title", "Untitled"),
            "dek": desc or "Historia seleccionada por el editor automático de WEEKLY.",
            "summary": desc or "WEEKLY seleccionó esta historia a partir de su feed.",
            "why_it_matters": "La historia fue seleccionada por su relevancia editorial, actualidad o interés dentro de la edición.",
            "key_points": ["Historia seleccionada para esta edición.", f"Fuente: {a.get('source', 'Unknown')}."]
        })
    return {
        "cover_story": fallback[0] if fallback else 0,
        "selected_ids": fallback,
        "stories": stories,
        "sections": [{"name": "WEEKLY PICKS", "ids": fallback}],
        "editor_note": "El editor IA no estuvo disponible; WEEKLY utilizó la selección automática de respaldo.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "model": "fallback",
        "status": "fallback",
        "error": error,
        "editorial_profile": EDITORIAL_PROFILE
    }


with open(ARTICLES, encoding="utf-8") as f:
    data = json.load(f)
articles = data.get("articles", [])
if not articles:
    raise RuntimeError("No articles available. Run the RSS fetch first.")

try:
    editorial = call_openai(articles)
    valid = set(range(len(articles)))
    editorial["selected_ids"] = [i for i in editorial.get("selected_ids", []) if i in valid][:24]
    if editorial.get("cover_story") not in valid:
        editorial["cover_story"] = editorial["selected_ids"][0] if editorial["selected_ids"] else 0

    # Keep only story treatments whose article IDs were selected and valid.
    selected = set(editorial["selected_ids"])
    cleaned_stories = []
    for story in editorial.get("stories", []):
        aid = story.get("article_id")
        if aid in selected and aid in valid:
            cleaned_stories.append(story)
    editorial["stories"] = cleaned_stories[:24]

    editorial["generatedAt"] = datetime.now(timezone.utc).isoformat()
    editorial["model"] = MODEL
    editorial["status"] = "ai"
    editorial["editorial_profile"] = EDITORIAL_PROFILE
except Exception as e:
    editorial = fallback_editorial(articles, str(e))

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(editorial, f, ensure_ascii=False, indent=2)

print(
    "Editorial issue:", editorial.get("status"),
    "selected:", len(editorial.get("selected_ids", [])),
    "editorial stories:", len(editorial.get("stories", []))
)
if editorial.get("status") == "fallback":
    print("Fallback reason:", editorial.get("error", "unknown"))
