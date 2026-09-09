import copy, json
from datetime import datetime, timezone
from pathlib import Path

ARTICLES = Path("data/articles.json")
EDITORIAL = Path("data/editorial.json")
FEEDS = Path("data/feeds.json")
ISSUES_DIR = Path("data/issues")
INDEX = ISSUES_DIR / "index.json"

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_snapshot():
    editorial = load(EDITORIAL, {})
    if not editorial.get("locked") or not editorial.get("issueNumber"):
        print("No locked issue to snapshot.")
        return False
    number = str(editorial["issueNumber"])
    articles_data = load(ARTICLES, {})
    articles = articles_data.get("articles", [])
    selected_ids = [i for i in (editorial.get("selected_ids") or []) if isinstance(i, int) and 0 <= i < len(articles)]
    feeds = load(FEEDS, {}).get("feeds", [])
    snapshot_path = ISSUES_DIR / f"issue-{number}.json"
    payload = {
        "schemaVersion": 1,
        "issueNumber": editorial.get("issueNumber"),
        "issueWindow": editorial.get("issueWindow") or articles_data.get("issueWindow") or {},
        "locked": True,
        "generatedAt": editorial.get("generatedAt") or datetime.now(timezone.utc).isoformat(),
        "archivedAt": datetime.now(timezone.utc).isoformat(),
        "editorial": copy.deepcopy(editorial),
        "articles": copy.deepcopy(articles),
        "clusters": copy.deepcopy(articles_data.get("clusters") or []),
        "selected_ids": selected_ids,
        "sourceCount": len([f for f in feeds if f.get("enabled", True)]),
        "sources": copy.deepcopy(feeds),
    }
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    idx = load(INDEX, {"issues": []})
    issues = idx.get("issues", []) if isinstance(idx, dict) else []
    window = payload["issueWindow"] or {}
    entry = {
        "number": editorial.get("issueNumber"),
        "start": window.get("start", ""),
        "end": window.get("end", ""),
        "stories": len(selected_ids),
        "locked": True,
        "cover": editorial.get("coverImage") or "assets/weekly-cover-fallback.svg",
        "pdf": f"data/issues/issue-{number}.pdf" if (ISSUES_DIR / f"issue-{number}.pdf").exists() else "",
        "file": f"data/issues/issue-{number}.json",
        "sourceCount": payload["sourceCount"],
    }
    issues = [x for x in issues if str(x.get("number")) != number]
    issues.append(entry)
    issues.sort(key=lambda x: int(x.get("number") or 0), reverse=True)
    INDEX.write_text(json.dumps({"issues": issues}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Archived issue #{number} -> {snapshot_path}")
    return True

if __name__ == "__main__":
    write_snapshot()
