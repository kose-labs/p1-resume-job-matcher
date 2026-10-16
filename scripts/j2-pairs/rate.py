"""Rate CV–job pairs in the browser, one at a time, straight into your rating sheet (J2).

    uv run python rate.py semanu              # the main set, p021-p120
    uv run python rate.py kobi --split dev    # only the main set's dev pairs
    uv run python rate.py kobi --batch calibration

Opens http://127.0.0.1:8765 with the job description on the left and the CV on the right. Press
1-5 to rate and move on, N to add a note, the arrow keys to go back and forth, and ? for the
protocol's scale and rules. Every rating is written to `data/ratings/<rater>.csv` at once, so you
can stop at any time and pick up where you left off.

The page shows only the pair ID and the two texts: never the stratum, the split or a model score
(annotation protocol, rules 2 and 4). It listens on this computer only.
"""

import argparse
import csv
import json
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RATERS = ("kobi", "semanu")
BATCHES = {"calibration": "yes", "main": "no"}
MAX_NOTE = 300
PAGE = Path(__file__).with_name("rate.html")


class Sheet:
    """A rater's sheet: pair_id -> (rating, notes), saved after every change."""

    def __init__(self, path: Path) -> None:
        """Load the sheet that `build_pairs.py` created."""
        if not path.exists():
            raise SystemExit(f"{path} is missing: run build_pairs.py first")
        self.path = path
        with path.open(encoding="utf-8", newline="") as f:
            self.rows = {r["pair_id"]: (r["rating"], r["notes"]) for r in csv.DictReader(f)}

    def set(self, pair_id: str, rating: int | None, notes: str) -> None:
        """Record a rating (None clears it) and write the whole sheet atomically."""
        self.rows[pair_id] = ("" if rating is None else str(rating), notes)
        partial = self.path.with_suffix(".tmp")
        with partial.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(["pair_id", "rating", "notes"])
            writer.writerows([pid, rating, note] for pid, (rating, note) in self.rows.items())
        os.replace(partial, self.path)  # never leaves a half-written sheet


def load_jsonl(path: Path) -> list[dict[str, str]]:
    """Read a JSONL file of the corpus or the pair set."""
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


class Session:
    """Everything one rating session needs: the batch's pairs, the texts and the sheet."""

    def __init__(self, root: Path, rater: str, batch: str, split: str = "all") -> None:
        """Load the pairs of `batch` (and `split`), the corpus texts and `rater`'s sheet."""
        data = root / "data"
        pairs = load_jsonl(data / "pairs" / "pairs.jsonl")
        # The split only chooses which pairs to serve; the page itself never learns it.
        self.order = [
            p["pair_id"]
            for p in pairs
            if p["calibration"] == BATCHES[batch] and split in ("all", p["split"])
        ]
        self.pairs = {p["pair_id"]: p for p in pairs}
        docs = load_jsonl(data / "corpus" / "jds.jsonl") + load_jsonl(data / "corpus" / "cvs.jsonl")
        self.docs = {d["id"]: d for d in docs}
        self.sheet = Sheet(data / "ratings" / f"{rater}.csv")
        self.rater = rater

    def state(self) -> dict[str, Any]:
        """The batch's pair IDs in rating order, and the ratings so far."""
        ratings = {
            pid: {"rating": int(r), "notes": n}
            for pid, (r, n) in self.sheet.rows.items()
            if pid in self.pairs and r.strip()
        }
        return {"rater": self.rater, "order": self.order, "ratings": ratings}

    def pair(self, pair_id: str) -> dict[str, Any]:
        """What the rater may see of a pair: its ID and the two texts, nothing else."""
        p = self.pairs[pair_id]
        jd, cv = self.docs[p["jd_id"]], self.docs[p["cv_id"]]
        return {
            "pair_id": pair_id,
            "job": {"title": jd["title"], "text": jd["text"]},
            "cv": {
                "title": cv["title"],
                "exp_years": cv.get("exp_years") or "",
                "text": cv["text"],
            },
        }

    def rate(self, body: dict[str, Any]) -> dict[str, Any]:
        """Validate and save one rating; returns the new state."""
        pair_id, rating, notes = body.get("pair_id"), body.get("rating"), body.get("notes", "")
        if pair_id not in self.order:
            raise ValueError("unknown pair")
        if rating is not None and (type(rating) is not int or not 1 <= rating <= 5):
            raise ValueError("rating must be a whole number from 1 to 5")
        if not isinstance(notes, str) or len(notes) > MAX_NOTE:
            raise ValueError(f"notes must be text of at most {MAX_NOTE} characters")
        self.sheet.set(pair_id, rating, " ".join(notes.split()))
        return self.state()


def make_handler(session: Session) -> type[BaseHTTPRequestHandler]:
    """A request handler bound to one session: the page, two reads and one write."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                self._json(200, session.state())
            elif self.path.startswith("/api/pair/") and self.path[10:] in session.order:
                self._json(200, session.pair(self.path[10:]))
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path != "/api/rate":
                self._json(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                self._json(200, session.rate(json.loads(self.rfile.read(min(length, 10_000)))))
            except (ValueError, json.JSONDecodeError) as error:
                self._json(400, {"error": str(error)})

        def _json(self, status: int, body: dict[str, Any]) -> None:
            self._send(status, json.dumps(body).encode(), "application/json")

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            pass  # keep the terminal quiet: progress is on the page

    return Handler


def main() -> None:
    """Parse the command line, load the session and serve the rating page until Ctrl+C."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("rater", choices=RATERS)
    parser.add_argument("--batch", choices=list(BATCHES), default="main")
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()

    session = Session(args.root, args.rater, args.batch, args.split)
    done = len(session.state()["ratings"].keys() & set(session.order))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(session))
    url = f"http://127.0.0.1:{args.port}/"
    which = args.batch if args.split == "all" else f"{args.batch} batch's {args.split}"
    print(f"Rating the {which} pairs as {args.rater}: {done} of {len(session.order)} done.")
    print(f"Open {url} (Ctrl+C here to stop; every rating is already saved).")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Your ratings are in", session.sheet.path.relative_to(args.root))


if __name__ == "__main__":
    main()
