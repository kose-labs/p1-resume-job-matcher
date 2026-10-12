"""Load-test the running API with near-limit CVs and check the container's peak memory (S9).

CI starts the Docker image with Render Free's memory (512 MB), then runs, from `backend/`:

    uv run python -m scripts.memory_check --container app --limit-mb 400

It builds a synthetic 10-page PDF just under the 5 MB upload limit (text plus incompressible
images, a fictional person), sends several matches at once, and fails if any request doesn't
succeed or if the container's peak memory goes over `--limit-mb`. Peak memory comes from the
container's cgroup (`memory.peak`), so it includes Python, the libraries and every request.
"""

import argparse
import io
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import httpx2
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.extract import MAX_PAGES
from app.limits import MAX_CV_BYTES

JD = "We are hiring a backend engineer to build and run REST APIs in Python with FastAPI. " * 3


def _pdf_with_images(side: int) -> bytes:
    """A MAX_PAGES-page CV, each page with text and a side x side image of random pixels."""
    _, height = A4
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for page in range(MAX_PAGES):
        noise = Image.frombytes("RGB", (side, side), os.urandom(side * side * 3))
        pdf.drawImage(ImageReader(noise), 50, height - 560, width=480, height=480)
        for i in range(20):
            pdf.drawString(50, height - 600 - i * 12, f"Page {page + 1}: Jordan Example, line {i}.")
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def big_pdf() -> bytes:
    """The largest such CV that still fits under the upload limit.

    Random pixels don't compress, and reportlab adds encoding overhead, so start from images that
    would fill the limit and shrink them until the file fits.
    """
    side = math.isqrt(MAX_CV_BYTES // (MAX_PAGES * 3))
    while side > 50:
        data = _pdf_with_images(side)
        if len(data) <= MAX_CV_BYTES:
            return data
        side = int(side * 0.95)
    sys.exit("couldn't build a test PDF under the upload limit")


def peak_memory_mb(container: str) -> float:
    """Return the container's peak memory in MB, from its cgroup v2 `memory.peak`."""
    out = subprocess.run(
        ["docker", "exec", container, "cat", "/sys/fs/cgroup/memory.peak"],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(out.stdout.strip()) / 1_048_576


def main() -> None:
    """Send concurrent near-limit matches, then compare peak memory with the limit."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=4)
    parser.add_argument("--container", help="Docker container to read peak memory from")
    parser.add_argument("--limit-mb", type=float, default=400)
    args = parser.parse_args()

    pdf = big_pdf()
    print(f"test CV: {len(pdf) / 1_048_576:.1f} MB, {MAX_PAGES} pages; {args.requests} at once")

    def send(_: int) -> int:
        response = httpx2.post(
            f"{args.url}/api/v1/match",
            files={"cv": ("cv.pdf", pdf, "application/pdf")},
            data={"job_description": JD},
            timeout=120,
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=args.requests) as pool:
        statuses = list(pool.map(send, range(args.requests)))
    print(f"statuses: {statuses}")
    if any(status != 200 for status in statuses):
        sys.exit("not every match succeeded")

    if args.container:
        peak = peak_memory_mb(args.container)
        print(f"peak container memory: {peak:.0f} MB (limit {args.limit_mb:.0f} MB)")
        if peak > args.limit_mb:
            sys.exit("over the memory budget (ADR-0002, ADR-0004)")


if __name__ == "__main__":
    main()
