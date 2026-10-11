"""Build the rated pair set (J2) from the evaluation corpus (research/annotation_protocol.md).

Reads `data/corpus/{jds,cvs}.jsonl` (built by `scripts/k5-corpus`) and writes, all git-ignored:

- `data/pairs/pairs.jsonl`: 120 pairs with their stratum (same / nearby / unrelated), split
  (dev / test) and whether they are in the 20-pair calibration batch. **Not for raters.**
- `data/pairs/packet-calibration.html` and `data/pairs/packet-main.html`: what raters read. Pair
  ID, job description and CV only: no field labels, no strata, no scores.
- `data/ratings/<rater>.csv`: one empty sheet per rater, calibration pairs first. Never
  overwritten, so ratings can't be lost by re-running.

Every choice is drawn from one seeded random generator, so the same corpus always gives the same
pairs, IDs and split, on any machine.

    uv run python build_pairs.py
"""

import csv
import html
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus"
PAIRS = ROOT / "data" / "pairs"
RATINGS = ROOT / "data" / "ratings"

SEED = "kose-p1-j2"
RATERS = ["kobi", "semanu"]
# Each field has exactly one nearby field (protocol: "nearby" stratum).
NEARBY = {
    "Python": "Data Science",
    "Data Science": "Python",
    "Java": "JavaScript",
    "JavaScript": "Java",
    "QA": "DevOps",
    "DevOps": "QA",
}
DEV_JDS = 10  # the other 20 JDs are test
CALIBRATION = {"same": 10, "nearby": 5, "unrelated": 5}  # 20 dev pairs, same mix as the whole set

Record = dict[str, str]


def load(name: str) -> list[Record]:
    """Read one JSONL file of the corpus."""
    with (CORPUS / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def by_field(records: list[Record], rng: random.Random) -> dict[str, list[Record]]:
    """Group records by field, each group shuffled."""
    groups: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        groups[record["field"]].append(record)
    for group in groups.values():
        rng.shuffle(group)
    return dict(sorted(groups.items()))


def make_pairs(
    jds: dict[str, list[Record]], cvs: dict[str, list[Record]], rng: random.Random
) -> list[dict[str, str]]:
    """Give every JD 2 same-field CVs, 1 nearby-field CV and 1 unrelated CV.

    Same-field CVs rotate (JD k gets CVs k and k+1) and nearby ones follow k, so each CV gets the
    same number of those. The unrelated CV is drawn from the least-used candidates, so no single CV
    dominates the ratings.
    """
    pairs = []
    uses: Counter[str] = Counter()
    for field, field_jds in jds.items():
        same, near = cvs[field], cvs[NEARBY[field]]
        unrelated = [cv for f in cvs if f not in (field, NEARBY[field]) for cv in cvs[f]]
        for k, jd in enumerate(field_jds):
            fewest = min(uses[cv["id"]] for cv in unrelated)
            other = rng.choice([cv for cv in unrelated if uses[cv["id"]] == fewest])
            chosen = [
                (same[k % len(same)], "same"),
                (same[(k + 1) % len(same)], "same"),
                (near[k % len(near)], "nearby"),
                (other, "unrelated"),
            ]
            uses.update(cv["id"] for cv, _ in chosen)
            pairs += [{"jd_id": jd["id"], "cv_id": cv["id"], "stratum": s} for cv, s in chosen]
    return pairs


def split_jds(jds: dict[str, list[Record]], rng: random.Random) -> set[str]:
    """Pick the dev JDs: spread across fields, every field in both dev and test."""
    fields = list(jds)
    rng.shuffle(fields)
    per_field = Counter({f: DEV_JDS // len(fields) for f in fields})
    for f in fields[: DEV_JDS % len(fields)]:
        per_field[f] += 1
    return {jd["id"] for f in fields for jd in jds[f][: per_field[f]]}


def packet(title: str, pairs: list[dict[str, str]], docs: dict[str, Record]) -> str:
    """Render the pairs a rater reads: no fields, strata, splits or scores."""
    parts = [
        f"<!doctype html><meta charset='utf-8'><title>{title}</title>",
        "<style>body{font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:auto;padding:1em}"
        "section{border-top:3px solid #0b3d63;margin:2em 0;padding-top:.5em}"
        ".cols{display:grid;grid-template-columns:1fr 1fr;gap:1.5em}"
        "pre{white-space:pre-wrap;font:inherit;background:#f5f7fa;padding:.8em;border-radius:6px}"
        "h2{margin:.2em 0}</style>",
        f"<h1>{title}</h1><p>Rate each pair 1–5 in your sheet "
        "(<code>data/ratings/&lt;you&gt;.csv</code>) using only "
        "<code>research/annotation_protocol.md</code>. "
        "Rate alone; don't discuss until both are done.</p>",
    ]
    for p in pairs:
        jd, cv = docs[p["jd_id"]], docs[p["cv_id"]]
        exp = f" · {html.escape(cv['exp_years'])} years" if cv.get("exp_years") else ""
        parts.append(
            f"<section><h2>{p['pair_id']}</h2><div class='cols'>"
            f"<div><h3>Job: {html.escape(jd['title'])}</h3>"
            f"<pre>{html.escape(jd['text'])}</pre></div>"
            f"<div><h3>CV: {html.escape(cv['title'])}{exp}</h3>"
            f"<pre>{html.escape(cv['text'])}</pre></div></div></section>"
        )
    return "\n".join(parts)


def main() -> None:
    """Build pairs, split, calibration batch, rater packets and empty rating sheets."""
    rng = random.Random(SEED)
    jd_list, cv_list = load("jds.jsonl"), load("cvs.jsonl")
    jds, cvs = by_field(jd_list, rng), by_field(cv_list, rng)

    pairs = make_pairs(jds, cvs, rng)
    dev = split_jds(jds, rng)
    for p in pairs:
        p["split"] = "dev" if p["jd_id"] in dev else "test"

    calibration = []
    for stratum, n in CALIBRATION.items():
        pool = [p for p in pairs if p["split"] == "dev" and p["stratum"] == stratum]
        calibration += rng.sample(pool, n)
    rng.shuffle(calibration)
    in_calibration = {id(p) for p in calibration}
    rest = [p for p in pairs if id(p) not in in_calibration]
    rng.shuffle(rest)
    # IDs follow rating order, so p001-p020 are the calibration batch.
    for i, p in enumerate(calibration + rest, start=1):
        p["pair_id"] = f"p{i:03d}"
        p["calibration"] = "yes" if id(p) in in_calibration else "no"
    ordered = calibration + rest

    PAIRS.mkdir(parents=True, exist_ok=True)
    with (PAIRS / "pairs.jsonl").open("w", encoding="utf-8") as f:
        for p in ordered:
            f.write(json.dumps(p) + "\n")

    docs = {d["id"]: d for d in jd_list + cv_list}
    (PAIRS / "packet-calibration.html").write_text(
        packet("P1 rating packet: calibration batch (p001–p020)", calibration, docs), "utf-8"
    )
    (PAIRS / "packet-main.html").write_text(
        packet("P1 rating packet: main set (p021–p120)", rest, docs), "utf-8"
    )

    RATINGS.mkdir(parents=True, exist_ok=True)
    for rater in RATERS:
        sheet = RATINGS / f"{rater}.csv"
        if sheet.exists():
            print(f"kept existing {sheet.relative_to(ROOT)}")
            continue
        with sheet.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["pair_id", "rating", "notes"])
            writer.writerows([p["pair_id"], "", ""] for p in ordered)
        print(f"wrote empty sheet {sheet.relative_to(ROOT)}")

    print(f"{len(pairs)} pairs: {dict(Counter(p['stratum'] for p in pairs))}")
    print(f"split: {dict(Counter(p['split'] for p in pairs))} ({len(dev)} dev JDs)")
    print(f"calibration: {dict(Counter(p['stratum'] for p in calibration))}")


if __name__ == "__main__":
    main()
