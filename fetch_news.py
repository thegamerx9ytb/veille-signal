import os
import json
import re
import feedparser
from datetime import datetime, timezone
from time import mktime

DATA_FILE = "data.json"

# Chaque flux RSS est associé à sa catégorie
FEEDS = [
    ("https://feeds.feedburner.com/TheHackersNews", "Cybersécurité"),
    ("https://www.bleepingcomputer.com/feed/", "Cybersécurité"),
    ("https://krebsonsecurity.com/feed/", "Cybersécurité"),
    ("https://techcrunch.com/category/artificial-intelligence/feed/", "Intelligence Artificielle"),
    ("https://venturebeat.com/category/ai/feed/", "Intelligence Artificielle"),
    ("https://techcrunch.com/feed/", "Technologie"),
    ("https://www.theverge.com/rss/index.xml", "Technologie"),
]

# Mots-clés pour estimer le niveau d'importance (du plus fort au plus faible)
KEYWORDS_CRITIQUE = [
    "zero-day", "zero day", "exploited in the wild", "actively exploited",
    "ransomware", "critical vulnerability", "faille critique",
    "activement exploitée", "data breach", "massive breach", "npm supply chain",
]
KEYWORDS_ELEVE = [
    "vulnerability", "vulnérabilité", "patch", "faille", "exploit",
    "attack", "cyberattaque", "malware", "breach", "leak", "hacked",
    "backdoor", "phishing",
]

MAX_ITEMS_PER_FEED = 4
MAX_AGE_DAYS = 3


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower())[:60]


def clean_html(raw):
    text = re.sub(r"<[^>]+>", "", raw or "")
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:220] + "…") if len(text) > 220 else text


def guess_importance(title, summary):
    blob = (title + " " + summary).lower()
    if any(k in blob for k in KEYWORDS_CRITIQUE):
        return "Critique"
    if any(k in blob for k in KEYWORDS_ELEVE):
        return "Élevé"
    return "Moyen"


def entry_date(entry):
    for field in ("published_parsed", "updated_parsed"):
        val = getattr(entry, field, None)
        if val:
            return datetime.fromtimestamp(mktime(val), tz=timezone.utc)
    return datetime.now(timezone.utc)


def collect():
    now = datetime.now(timezone.utc)
    items = []
    for url, categorie in FEEDS:
        try:
            parsed = feedparser.parse(url)
        except Exception as e:
            print(f"Erreur sur {url} : {e}")
            continue
        for entry in parsed.entries[:MAX_ITEMS_PER_FEED]:
            pub = entry_date(entry)
            if (now - pub).days > MAX_AGE_DAYS:
                continue
            title = getattr(entry, "title", "").strip()
            summary = clean_html(getattr(entry, "summary", ""))
            source = parsed.feed.get("title", url) if hasattr(parsed, "feed") else url
            items.append({
                "titre": title,
                "resume": summary or "Pas de résumé disponible.",
                "categorie": categorie,
                "importance": guess_importance(title, summary),
                "date": pub.strftime("%Y-%m-%d"),
                "source": source,
                "lien": getattr(entry, "link", ""),
            })
    return items


def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"lastUpdate": None, "items": []}


def merge(existing, new_items):
    existing_keys = {slug(i["titre"]) + i.get("date", "") for i in existing["items"]}
    added = 0
    for item in new_items:
        key = slug(item["titre"]) + item["date"]
        if key not in existing_keys:
            existing["items"].insert(0, item)
            existing_keys.add(key)
            added += 1
    existing["items"].sort(key=lambda i: i.get("date", ""), reverse=True)
    existing["lastUpdate"] = datetime.now(timezone.utc).isoformat()
    return added


def main():
    existing = load_existing()
    new_items = collect()
    added = merge(existing, new_items)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"{added} nouveau(x) fait(s) ajouté(s). Total : {len(existing['items'])}")


if __name__ == "__main__":
    main()
