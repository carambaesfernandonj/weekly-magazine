import base64, json, os, re, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ARTICLES = "data/articles.json"
OUT = "data/editorial.json"
MANIFESTO = "data/manifesto.json"
COVER_DIR = Path("data/covers")
FALLBACK_COVER = "assets/weekly-cover-fallback.svg"
ISSUES_DIR = Path("data/issues")
ISSUES_INDEX = ISSUES_DIR / "index.json"
MODEL = os.environ.get("OPENAI_EDITOR_MODEL", "gpt-5.6-luna")
EDITORIAL_PROFILE = {
    "name": "Fernando Mode",
    "voice": "inteligente, curioso, informal y editorial",
    "humor": "seco y ocasional; nunca forzado",
    "attitude": "opinión clara pero justa, escéptica con el hype y atenta a conexiones raras",
    "writing": "titulares fuertes, párrafos cortos, explicaciones claras y remates ocasionales",
    "rule": "informar primero, entretener después; no inventar hechos"
}


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def issue_window(data):
    return data.get("issueWindow") or {"start": "", "end": "", "timezone": "UTC", "endExclusive": True}


def next_issue_number(previous):
    try:
        return int(previous or 0) + 1
    except Exception:
        return 1



def update_archive_index(issue):
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    data = load_json(ISSUES_INDEX, {"issues": []})
    issues = data.get("issues", []) if isinstance(data, dict) else []
    number = issue.get("issueNumber")
    entry = {
        "number": number,
        "start": (issue.get("issueWindow") or {}).get("start", ""),
        "end": (issue.get("issueWindow") or {}).get("end", ""),
        "stories": len(issue.get("selected_ids") or []),
        "locked": bool(issue.get("locked")),
        "cover": issue.get("coverImage") or FALLBACK_COVER,
        "pdf": f"data/issues/issue-{number}.pdf" if (ISSUES_DIR / f"issue-{number}.pdf").exists() else "",
        "file": f"data/issues/issue-{number}.json" if (ISSUES_DIR / f"issue-{number}.json").exists() else "",
    }
    issues = [x for x in issues if str(x.get("number")) != str(number)]
    issues.append(entry)
    issues.sort(key=lambda x: int(x.get("number") or 0), reverse=True)
    ISSUES_INDEX.write_text(json.dumps({"issues": issues}, ensure_ascii=False, indent=2), encoding="utf-8")


def fallback_editorial(articles, number, window, manifesto):
    selected = [i for i, a in enumerate(articles) if a.get("selected")]
    if len(selected) < 12:
        selected = list(range(min(24, len(articles))))
    stories = []
    for i in selected:
        a = articles[i]
        desc = (a.get("description") or "").strip()
        if len(desc) > 900:
            desc = desc[:897].rstrip() + "..."
        stories.append({
            "article_id": i,
            "headline": a.get("title", "Sin título"),
            "dek": desc or "Historia publicada por la fuente original.",
            "summary": desc or "Consulta la fuente original para leer la historia completa.",
            "source": a.get("source", "Fuente original"),
        })
    return {
        "issueNumber": number,
        "issueWindow": window,
        "locked": True,
        "status": "rss",
        "model": "zero-cost",
        "headline": "UNA SEMANA. UN NÚMERO.",
        "editorial": manifesto.get("body", "WEEKLY presenta el material original de sus fuentes."),
        "editorialSource": "manifesto",
        "coverImage": FALLBACK_COVER,
        "coverSource": "fallback",
        "coverPrompt": "",
        "coverStory": selected[0] if selected else 0,
        "selected_ids": selected,
        "stories": stories,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "editorial_profile": EDITORIAL_PROFILE,
    }


def api_json(url, payload, api_key):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def response_text(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get("output_text"), str):
            return obj["output_text"]
        for item in obj.get("output", []) or []:
            for c in item.get("content", []) or []:
                if isinstance(c, dict) and isinstance(c.get("text"), str):
                    return c["text"]
    return ""


def generate_editorial(articles, selected_ids, number, window, api_key):
    digest = []
    for i in selected_ids:
        a = articles[i]
        digest.append({
            "id": i,
            "source": a.get("source", ""),
            "topic": a.get("category", "Other"),
            "title": a.get("title", ""),
            "summary": (a.get("description") or "")[:700],
        })
    prompt = f"""Eres el editor de WEEKLY, una revista semanal personal. Escribe la editorial de apertura del número #{number}.

Tono Fernando Mode: inteligente, curioso, informal, con humor seco ocasional, opinión clara pero justa, escéptico con el hype y atento a conexiones inesperadas. Debe sonar como una persona con criterio, no como marketing corporativo. Puedes hacer una observación divertida, pero no fuerces chistes. No inventes datos ni afirmes cosas que no aparecen en el material.

La editorial debe tener 180-280 palabras, en español, y conectar varias historias de esta edición en vez de resumirlas una por una. Debe funcionar como texto de apertura de una revista.

Devuelve EXACTAMENTE dos bloques usando estas etiquetas:
HEADLINE: un titular breve en español, de máximo 80 caracteres.
BODY: la editorial completa.

Semana: {window.get('start','')} → {window.get('end','')}

Historias seleccionadas:
{json.dumps(digest, ensure_ascii=False, indent=2)}"""
    payload = {
        "model": MODEL,
        "input": prompt,
        "max_output_tokens": 700,
    }
    raw = response_text(api_json("https://api.openai.com/v1/responses", payload, api_key))
    mh = re.search(r"HEADLINE:\s*(.+)", raw)
    mb = re.search(r"BODY:\s*(.*)", raw, re.S)
    if not mh or not mb:
        raise ValueError("La respuesta de IA no tuvo el formato esperado")
    headline = mh.group(1).strip().strip('"')
    body = mb.group(1).strip()
    if len(body) < 120:
        raise ValueError("La editorial generada es demasiado corta")
    return headline[:120], body


def generate_cover(prompt, api_key, issue_number):
    COVER_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "size": "1024x1536",
    }
    obj = api_json("https://api.openai.com/v1/images/generations", payload, api_key)
    data = (obj.get("data") or [{}])[0]
    b64 = data.get("b64_json")
    if not b64:
        raise ValueError("La API de imagen no devolvió b64_json")
    out = COVER_DIR / f"issue-{issue_number}.png"
    out.write_bytes(base64.b64decode(b64))
    return str(out).replace("\\", "/")


def write_issue_snapshot(issue, articles_data):
    if not issue.get("locked") or not issue.get("issueNumber"):
        return
    number = str(issue.get("issueNumber"))
    selected_ids = [i for i in (issue.get("selected_ids") or []) if isinstance(i, int) and 0 <= i < len(articles_data.get("articles", []))]
    feeds = load_json("data/feeds.json", {}).get("feeds", [])
    snapshot = {
        "schemaVersion": 1,
        "issueNumber": issue.get("issueNumber"),
        "issueWindow": issue.get("issueWindow") or articles_data.get("issueWindow") or {},
        "locked": True,
        "generatedAt": issue.get("generatedAt") or datetime.now(timezone.utc).isoformat(),
        "archivedAt": datetime.now(timezone.utc).isoformat(),
        "editorial": issue,
        "articles": articles_data.get("articles", []),
        "clusters": articles_data.get("clusters", []),
        "selected_ids": selected_ids,
        "sourceCount": len([f for f in feeds if f.get("enabled", True)]),
        "sources": feeds,
    }
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    (ISSUES_DIR / f"issue-{number}.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


articles_data = load_json(ARTICLES, {})
articles = articles_data.get("articles", [])
if not articles:
    raise RuntimeError("No hay artículos disponibles. Ejecuta primero el fetch RSS.")
window = issue_window(articles_data)
manifesto = load_json(MANIFESTO, {})
existing = load_json(OUT, {})

# ISSUE LOCK: once a weekly issue is created, rerunning the workflow for the same
# editorial window must not regenerate its editorial or cover.
if existing.get("locked") and existing.get("issueWindow") == window and os.environ.get("FORCE_REGENERATE_ISSUE", "false").lower() != "true":
    print(f"Issue #{existing.get('issueNumber','?')} is locked for {window.get('start')} → {window.get('end')}; keeping it unchanged.")
    write_issue_snapshot(existing, articles_data)
    update_archive_index(existing)
    raise SystemExit(0)

number = next_issue_number(existing.get("issueNumber") or 36)
selected = [i for i, a in enumerate(articles) if a.get("selected")]
if not selected:
    selected = list(range(min(24, len(articles))))

result = fallback_editorial(articles, number, window, manifesto)
result["selected_ids"] = selected
result["stories"] = [{
    "article_id": i,
    "headline": articles[i].get("title", "Sin título"),
    "dek": (articles[i].get("description") or "")[:900],
    "summary": (articles[i].get("description") or "")[:900],
    "source": articles[i].get("source", "Fuente original"),
} for i in selected]

api_key = os.environ.get("OPENAI_API_KEY", "").strip()
if api_key:
    try:
        headline, body = generate_editorial(articles, selected, number, window, api_key)
        result["headline"] = headline
        result["editorial"] = body
        result["editorialSource"] = "ai"
        result["status"] = "ai"
        result["model"] = MODEL
        print("AI editorial generated.")
    except Exception as e:
        print(f"AI editorial unavailable; using manifesto fallback: {e}")

    try:
        top = [
            {"source": articles[i].get("source", ""), "title": articles[i].get("title", ""), "summary": (articles[i].get("description") or "")[:400]}
            for i in selected[:16]
        ]
        cover_prompt = f"""Editorial magazine cover for WEEKLY issue #{number}. Visual language inspired by glossy videogame, film and technology magazines from the early 2000s: bold Y2K editorial design, dramatic central visual, slightly chaotic but deliberate cover composition, glossy print feel, strong shapes, energetic lighting, subtle retro-futurist details. The cover should feel like a real magazine, not a generic poster. No readable words, no fake logos, no watermarks, no UI, no collage of unrelated tiny objects. Build one coherent visual metaphor from these weekly themes and stories: {json.dumps(top, ensure_ascii=False)}"""
        result["coverPrompt"] = cover_prompt
        result["coverImage"] = generate_cover(cover_prompt, api_key, number)
        result["coverSource"] = "ai"
        print("AI cover generated.")
    except Exception as e:
        print(f"AI cover unavailable; using static fallback: {e}")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
write_issue_snapshot(result, articles_data)
update_archive_index(result)
print(f"Published WEEKLY issue #{number}: status={result['status']} cover={result['coverSource']} stories={len(selected)}")
