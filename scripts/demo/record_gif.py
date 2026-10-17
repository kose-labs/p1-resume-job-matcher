# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright==1.64.0", "pillow==13.0.0"]
# ///
"""Record the README demo GIF from the live site, with the sample data only (never a real CV).

    uv run scripts/demo/record_gif.py docs/screenshots/demo.gif

Uses the installed Google Chrome (`channel="chrome"`), so `playwright install` isn't needed. Waits
for the backend to wake up first, then takes a screenshot per step and joins them with Pillow,
960 px wide. The dependencies are pinned above, so a re-run draws the same way.
"""

import asyncio
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.async_api import Locator, Page, async_playwright

URL = "https://kose-labs.github.io/p1-resume-job-matcher/"
WIDTH = 960

# Headless screenshots have no pointer: draw one that follows the mouse.
CURSOR_CSS = """#demo-cursor{position:fixed;z-index:99999;width:22px;height:22px;
margin:-4px 0 0 -4px;pointer-events:none;transition:transform .12s}
#demo-cursor.down{transform:scale(.8)}"""
CURSOR_JS = """() => {
  const c = document.createElement('div'); c.id = 'demo-cursor';
  c.innerHTML = '<svg width="22" height="22" viewBox="0 0 22 22"><path d="M4 2 L4 18 L8.5 14 '
    + 'L11.5 20.5 L14 19.3 L11 13 L17 13 Z" fill="#111" stroke="#fff" stroke-width="1.5" '
    + 'stroke-linejoin="round"/></svg>';
  c.style.left = '640px'; c.style.top = '300px'; document.body.appendChild(c);
  addEventListener('mousemove', e => {
    c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'
  }, true);
  addEventListener('mousedown', () => c.classList.add('down'), true);
  addEventListener('mouseup', () => c.classList.remove('down'), true);
}"""


class Recorder:
    """Screenshots with how long each one is shown, and a mouse that moves smoothly."""

    def __init__(self, page: Page) -> None:
        """Start with no frames and the mouse in the middle of the page."""
        self.page = page
        self.frames: list[tuple[Image.Image, int]] = []
        self.pos = (640.0, 300.0)

    async def snap(self, ms: int) -> None:
        """Add a screenshot of the page, shown for `ms` milliseconds."""
        shot = await self.page.screenshot()
        self.frames.append((Image.open(io.BytesIO(shot)).convert("RGB"), ms))

    async def move_to(self, target: Locator, steps: int = 8) -> None:
        """Glide the mouse to the middle of `target`, one frame per step."""
        box = await target.bounding_box()
        assert box, "target isn't visible"
        tx, ty = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        x, y = self.pos
        for i in range(1, steps + 1):
            t = i / steps
            t = t * t * (3 - 2 * t)  # ease in and out
            await self.page.mouse.move(x + (tx - x) * t, y + (ty - y) * t)
            await self.snap(60)
        self.pos = (tx, ty)


async def record() -> list[tuple[Image.Image, int]]:
    """Run the demo on the live site and return its frames."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome")
        page = await browser.new_page(
            viewport={"width": 1280, "height": 760}, color_scheme="light"
        )
        await page.goto(URL)
        await page.get_by_text("Server ready").wait_for(timeout=150_000)
        await page.add_style_tag(content=CURSOR_CSS)
        await page.evaluate(CURSOR_JS)
        await page.mouse.move(640, 300)
        await page.wait_for_timeout(500)
        rec = Recorder(page)

        await rec.snap(1800)  # the empty page
        sample = page.get_by_role("button", name="Use sample data")
        await rec.move_to(sample)
        await rec.snap(500)
        await sample.click()
        await page.get_by_text("sample-cv.pdf").wait_for()
        await page.wait_for_timeout(300)
        await rec.snap(2000)  # filled in
        run = page.get_by_role("button", name="Run match")
        await rec.move_to(run)
        await rec.snap(500)
        await run.click()
        for _ in range(60):  # loading, until the result appears
            await rec.snap(100)
            if await page.get_by_text("Estimated fit").count():
                break
        for _ in range(8):  # the meter draws in
            await rec.snap(100)
        await rec.snap(4500)  # the result
        about = page.get_by_text("About this score")
        await about.scroll_into_view_if_needed()
        await rec.move_to(about)
        await about.click()
        await page.wait_for_timeout(400)
        await page.mouse.wheel(0, 400)
        await page.wait_for_timeout(500)
        await rec.snap(4000)  # the explanation
        await browser.close()
        return rec.frames


def save_gif(frames: list[tuple[Image.Image, int]], out: Path) -> None:
    """Scale the frames to WIDTH, reduce them to 128 colours and write a looping GIF."""
    images = []
    for image, _ in frames:
        small = image.resize(
            (WIDTH, round(image.height * WIDTH / image.width)), Image.LANCZOS
        )
        images.append(small.quantize(colors=128, dither=Image.Dither.NONE))
    images[0].save(
        out,
        save_all=True,
        append_images=images[1:],
        duration=[ms for _, ms in frames],
        loop=0,
        optimize=True,
    )
    print(f"{len(images)} frames, {out.stat().st_size // 1024} KB -> {out}")


if __name__ == "__main__":
    save_gif(asyncio.run(record()), Path(sys.argv[1]))
