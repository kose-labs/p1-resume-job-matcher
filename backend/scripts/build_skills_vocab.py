"""Build the skill vocabulary for skill extraction (K9) from the ESCO API.

ESCO (the EU's skills taxonomy) is free to reuse with attribution under the Commission's reuse
policy (Decision 2011/833/EU). The full download needs a form, so this script walks the public
API instead, from a few branches of the taxonomy that cover what tech job descriptions ask for:

- `isced-f/061` information and communication technologies: languages, frameworks, databases,
  tools, methods (Python, Kubernetes, agile development…), as knowledge concepts.
- `isced-f/0542` statistics and `isced-f/0541` mathematics: data science foundations.
- skill group `S5` working with computers: hands-on digital skills ("use version control
  systems", "administer databases").

Every concept below a root is collected with its preferred and alternative English labels.
Responses are cached in the git-ignored `data/raw/esco/`, so a re-run is offline and
reproducible. The output, `app/ml/artifacts/skills-esco.json.gz`, holds only labels and URIs
(gzipped with a fixed header, so the same input gives the same bytes).

Run from `backend/`:  uv run python -m scripts.build_skills_vocab
"""

import gzip
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "raw" / "esco"
OUT = Path(__file__).resolve().parents[1] / "app" / "ml" / "artifacts" / "skills-esco.json.gz"

API = "https://ec.europa.eu/esco/api/resource"
VERSION = "v1.2.0"
ROOTS = [
    ("concept", "http://data.europa.eu/esco/isced-f/061"),
    ("concept", "http://data.europa.eu/esco/isced-f/0542"),
    ("concept", "http://data.europa.eu/esco/isced-f/0541"),
    # S5 "working with computers"; v1.2 replaced the S-codes with UUIDs.
    ("skill", "http://data.europa.eu/esco/skill/243eb885-07c7-4b77-ab9c-827551d83dc4"),
]
CHILD_LINKS = ("narrowerConcept", "narrowerSkill")


def fetch(kind: str, uri: str) -> dict:
    """Return one ESCO resource, from the cache when possible."""
    name = uri.rsplit("/", 1)[-1] + ".json"
    cached = CACHE / kind / name
    if cached.exists():
        return json.loads(cached.read_text("utf-8"))
    query = urllib.parse.urlencode({"uri": uri, "language": "en", "selectedVersion": VERSION})
    with urllib.request.urlopen(f"{API}/{kind}?{query}", timeout=120) as resp:
        data = json.load(resp)
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(data), "utf-8")
    return data


def children(resource: dict) -> list[tuple[str, str]]:
    """The narrower concepts and skills of a resource, as (kind, uri)."""
    links = resource.get("_links", {})
    out = []
    for key in CHILD_LINKS:
        for link in links.get(key, []):
            kind = "skill" if "/skill/" in link["uri"] else "concept"
            out.append((kind, link["uri"]))
    return out


def crawl() -> dict[str, dict]:
    """Breadth-first walk from the roots; returns uri -> skill resource."""
    seen: set[str] = set()
    skills: dict[str, dict] = {}
    frontier = ROOTS
    with ThreadPoolExecutor(max_workers=8) as pool:
        while frontier:
            frontier = [(k, u) for k, u in frontier if u not in seen]
            seen.update(u for _, u in frontier)
            resources = list(pool.map(lambda ku: fetch(*ku), frontier))
            nxt = []
            for (kind, uri), res in zip(frontier, resources, strict=True):
                if kind == "skill":
                    skills[uri] = res
                nxt += children(res)
            frontier = nxt
            print(f"fetched {len(seen)} concepts, {len(skills)} skills")
    return skills


def labels(resource: dict) -> tuple[str, list[str]]:
    """Preferred and alternative English labels of a skill."""
    preferred = resource.get("preferredLabel", {}).get("en") or resource.get("title", "")
    alternatives = resource.get("alternativeLabel", {}).get("en", []) or []
    return preferred, sorted(set(alternatives) - {preferred})


def main() -> None:
    """Crawl, then write the vocabulary sorted by URI so the file is stable across runs."""
    skills = crawl()
    entries = []
    for uri in sorted(skills):
        res = skills[uri]
        if "hasSkillType" not in res.get("_links", {}):
            continue  # skill groups (S5, S5.1…) are headings, not skills
        preferred, alternatives = labels(res)
        if preferred:
            entries.append({"uri": uri, "label": preferred, "alt": alternatives})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "ESCO " + VERSION + " (European Commission), https://esco.ec.europa.eu",
        "licence": "Reuse with attribution, Commission Decision 2011/833/EU",
        "roots": [uri for _, uri in ROOTS],
        "skills": entries,
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with OUT.open("wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as gz:
        gz.write(raw)
    print(f"wrote {len(entries)} skills to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
