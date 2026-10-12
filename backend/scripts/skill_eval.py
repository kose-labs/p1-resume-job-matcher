"""Hand labels and evaluation for skill extraction (K9).

    uv run python -m scripts.skill_eval packet               # pick 20 JDs, write the packet
    uv run python -m scripts.skill_eval evaluate             # precision / recall / F1 on dev
    uv run python -m scripts.skill_eval evaluate --split test

**packet** picks 20 job descriptions from the evaluation corpus, keeping the J2 split: 8 of the
10 dev JDs and 12 of the 20 test JDs, spread across the six fields. It writes the packet to read,
`data/skills/packet.html` (git-ignored, like all corpus text), and an empty sheet,
`research/skill_labels/kobi.csv`, which is never overwritten. The labelling rules are in
`research/skill_labeling_guide.md`. Label **before** looking at what the extractor finds.

**evaluate** compares the extractor's skills with the hand labels, per JD, then sums the counts
(micro-averaged precision, recall and F1, the plan's metric). A hand label is turned into the
extractor's name for it when the extractor recognises it ("Postgres" -> "PostgreSQL"); a label
it doesn't recognise can only be a miss, which is the vocabulary gap we want to see. On dev it
also lists every false positive and miss, to learn from; on test it prints the totals only.

Run from `backend/`. Needs `data/corpus/jds.jsonl` and `data/pairs/pairs.jsonl` (J2).
"""

import argparse
import csv
import html
import json
import random
from collections import defaultdict
from pathlib import Path

from app.ml.skills import SkillExtractor

ROOT = Path(__file__).resolve().parents[2]
JDS = ROOT / "data" / "corpus" / "jds.jsonl"
PAIRS = ROOT / "data" / "pairs" / "pairs.jsonl"
PACKET = ROOT / "data" / "skills" / "packet.html"
LABELS = ROOT / "research" / "skill_labels" / "kobi.csv"

SEED = "kose-p1-k9"
TAKE = {"dev": 8, "test": 12}
LEVELS = ("required", "nice")


def load_jds() -> dict[str, dict[str, str]]:
    """Corpus job descriptions by ID."""
    with JDS.open(encoding="utf-8") as f:
        return {d["id"]: d for d in map(json.loads, f)}


def jd_splits() -> dict[str, str]:
    """JD ID -> dev or test, from the J2 pair set."""
    with PAIRS.open(encoding="utf-8") as f:
        return {p["jd_id"]: p["split"] for p in map(json.loads, f)}


def choose(splits: dict[str, str], jds: dict[str, dict[str, str]]) -> dict[str, str]:
    """Pick the labelled JDs: round-robin over fields, so every field is in dev and test."""
    rng = random.Random(SEED)
    chosen: dict[str, str] = {}
    for split, n in TAKE.items():
        by_field: dict[str, list[str]] = defaultdict(list)
        for jd_id in sorted(j for j, s in splits.items() if s == split):
            by_field[jds[jd_id]["field"]].append(jd_id)
        for ids in by_field.values():
            rng.shuffle(ids)
        queue = [ids for _, ids in sorted(by_field.items())]
        picked: list[str] = []
        while len(picked) < n and any(queue):
            for ids in queue:
                if ids and len(picked) < n:
                    picked.append(ids.pop(0))
        chosen |= dict.fromkeys(picked, split)
    return dict(sorted(chosen.items()))


def packet() -> None:
    """Write the reading packet and, if missing, the empty label sheet."""
    jds = load_jds()
    chosen = choose(jd_splits(), jds)
    parts = [
        "<!doctype html><meta charset='utf-8'><title>P1 skill labelling (K9)</title>",
        "<style>body{font:15px/1.5 system-ui,sans-serif;max-width:900px;margin:auto;padding:1em}"
        "section{border-top:3px solid #0b3d63;margin:2em 0;padding-top:.5em}"
        "pre{white-space:pre-wrap;font:inherit;background:#f5f7fa;padding:.8em;border-radius:6px}"
        "</style><h1>Skill labelling packet (K9): 20 job descriptions</h1>"
        "<p>For each JD, add one row per skill to <code>research/skill_labels/kobi.csv</code>, "
        "following <code>research/skill_labeling_guide.md</code>.</p>",
    ]
    for jd_id in chosen:
        jd = jds[jd_id]
        parts.append(
            f"<section><h2>{jd_id}</h2><h3>{html.escape(jd['title'])}</h3>"
            f"<pre>{html.escape(jd['text'])}</pre></section>"
        )
    PACKET.parent.mkdir(parents=True, exist_ok=True)
    PACKET.write_text("\n".join(parts), "utf-8")
    print(f"wrote {PACKET.relative_to(ROOT)}: {len(chosen)} JDs")
    if LABELS.exists():
        print(f"kept existing {LABELS.relative_to(ROOT)}")
        return
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    with LABELS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["jd_id", "skill", "level"])
        writer.writerows([jd_id, "", ""] for jd_id in chosen)
    print(f"wrote empty sheet {LABELS.relative_to(ROOT)}")


def read_labels() -> dict[str, set[tuple[str, str]]]:
    """JD ID -> {(skill, level)} from the sheet, skipping empty rows."""
    labels: dict[str, set[tuple[str, str]]] = defaultdict(set)
    with LABELS.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            skill, level = row["skill"].strip(), (row["level"].strip().lower() or "required")
            if not skill:
                continue
            if level not in LEVELS:
                raise SystemExit(f"{row['jd_id']}: level must be one of {LEVELS}, not {level!r}")
            labels[row["jd_id"]].add((skill, level))
    return labels


def evaluate(split: str) -> None:
    """Print micro precision, recall and F1 of the extractor against the hand labels."""
    jds, splits, labels = load_jds(), jd_splits(), read_labels()
    extractor = SkillExtractor.load()

    def canonical(label: str) -> str:
        found = extractor.extract(label)
        return found[0].name.lower() if len(found) == 1 else label.lower()

    tp = fp = fn = 0
    required_hit = required_all = 0
    report = []
    for jd_id in sorted(j for j in labels if splits[j] == split):
        gold = {canonical(skill): level for skill, level in labels[jd_id]}
        predicted = {s.name.lower() for s in extractor.extract(jds[jd_id]["text"])}
        tp += len(predicted & gold.keys())
        fp += len(predicted - gold.keys())
        fn += len(gold.keys() - predicted)
        required = {s for s, level in gold.items() if level == "required"}
        required_hit += len(required & predicted)
        required_all += len(required)
        report.append((jd_id, sorted(predicted - gold.keys()), sorted(gold.keys() - predicted)))
    if not report:
        raise SystemExit(f"no labelled JDs in split '{split}' yet")

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    print(f"{extractor.name} {extractor.version} on {split}: {len(report)} JDs")
    print(
        f"precision {precision:.3f} (target >= 0.80)   recall {recall:.3f}   "
        f"F1 {f1:.3f} (target >= 0.70)"
    )
    print(f"recall on required skills only: {required_hit}/{required_all}")
    if split == "dev":
        for jd_id, wrong, missed in report:
            print(
                f"\n{jd_id}\n  false positives: {', '.join(wrong) or '-'}"
                f"\n  missed: {', '.join(missed) or '-'}"
            )


def main() -> None:
    """Parse the command line and run the chosen step."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("packet", help="pick the JDs and write the labelling packet")
    ev = sub.add_parser("evaluate", help="precision, recall and F1 against the labels")
    ev.add_argument("--split", choices=["dev", "test"], default="dev")
    args = parser.parse_args()
    if args.command == "packet":
        packet()
    else:
        evaluate(args.split)


if __name__ == "__main__":
    main()
