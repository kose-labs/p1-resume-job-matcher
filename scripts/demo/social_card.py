# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright==1.64.0"]
# ///
"""Make the link-preview image from the live site's result, with the sample data only.

    uv run scripts/demo/social_card.py frontend/public/og-image.png 1200x630
    uv run scripts/demo/social_card.py social-preview.png 1280x640   # GitHub's Social preview

Runs the sample match on the live site, screenshots the result card and skills, and sets them
next to the page's headline in its own fonts and colours. Uses the installed Google Chrome
(`channel="chrome"`) and the fonts in `frontend/node_modules`, so run `npm ci` there first.
"""

import asyncio
import base64
import sys
from pathlib import Path

from playwright.async_api import Page, async_playwright

URL = "https://kose-labs.github.io/p1-resume-job-matcher/"
FONTS = Path(__file__).resolve().parents[2] / "frontend/node_modules/@fontsource"

CARD_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Plex;font-weight:400;src:url({sans400})}}
@font-face{{font-family:Plex;font-weight:600;src:url({sans600})}}
@font-face{{font-family:PlexMono;font-weight:400;src:url({mono400})}}
*{{margin:0;box-sizing:border-box}}
body{{width:{w}px;height:{h}px;overflow:hidden;display:flex;align-items:center;gap:48px;
  padding:0 0 0 64px;background:#fafafa;color:#18181b;font-family:Plex,sans-serif}}
.text{{flex:0 0 {text_w}px;display:flex;flex-direction:column;gap:24px}}
.brand{{font:400 22px PlexMono,monospace;color:#52525b}}
h1{{font-size:46px;line-height:1.15;font-weight:600;letter-spacing:-0.01em}}
p{{font-size:23px;line-height:1.4;color:#52525b}}
.url{{font:400 19px PlexMono,monospace;color:#166534}}
.shot{{flex:1;align-self:stretch;display:flex;align-items:center;overflow:hidden}}
.shot img{{width:{img_w}px;border:1px solid #e4e4e7;border-radius:14px;background:#fff;
  box-shadow:0 12px 32px rgb(0 0 0 / 10%)}}
</style></head><body>
<div class="text">
  <div class="brand">KoSe Labs · Resume–Job Matcher</div>
  <h1>See how well a CV fits a job, and which skills it's missing.</h1>
  <p>An estimated fit, and the job's skills the CV names and misses. Your CV is never stored.</p>
  <div class="url">kose-labs.github.io/p1-resume-job-matcher</div>
</div>
<div class="shot"><img src="data:image/png;base64,{shot}"></div>
</body></html>"""


def font(path: str) -> str:
    """A font file from `frontend/node_modules` as a data URL."""
    data = base64.b64encode((FONTS / path).read_bytes()).decode()
    return f"data:font/woff2;base64,{data}"


async def result_shot(page: Page) -> bytes:
    """Run the sample match on the live site and screenshot the result card and skills."""
    await page.goto(URL)
    await page.get_by_text("Server ready").wait_for(timeout=150_000)
    await page.get_by_role("button", name="Use sample data").click()
    await page.get_by_text("sample-cv.pdf").wait_for()
    await page.get_by_role("button", name="Run match").click()
    await page.get_by_text("Estimated fit · TF-IDF").wait_for()
    await page.wait_for_timeout(1500)  # the meter draws in
    card = await page.locator("[data-band]").first.bounding_box()
    tip = await page.get_by_text("Have any of the missing skills?").bounding_box()
    assert card and tip, "result isn't visible"
    pad = 20
    bottom = tip["y"] + tip["height"] + 8  # above the divider under the tip
    return await page.screenshot(
        clip={
            "x": card["x"] - pad,
            "y": card["y"] - pad,
            "width": card["width"] + 2 * pad,
            "height": bottom - card["y"] + pad,
        }
    )


async def main(out: Path, w: int, h: int) -> None:
    """Write the preview image, `w` × `h` pixels, to `out`."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome")
        page = await browser.new_page(
            viewport={"width": 1280, "height": 900},
            color_scheme="light",
            device_scale_factor=2,
        )
        shot = base64.b64encode(await result_shot(page)).decode()
        card = await browser.new_page(viewport={"width": w, "height": h})
        text_w = round(w * 0.4)
        await card.set_content(
            CARD_HTML.format(
                w=w,
                h=h,
                text_w=text_w,
                img_w=round(w * 0.58),
                shot=shot,
                sans400=font(
                    "ibm-plex-sans/files/ibm-plex-sans-latin-400-normal.woff2"
                ),
                sans600=font(
                    "ibm-plex-sans/files/ibm-plex-sans-latin-600-normal.woff2"
                ),
                mono400=font(
                    "ibm-plex-mono/files/ibm-plex-mono-latin-400-normal.woff2"
                ),
            )
        )
        await card.evaluate("document.fonts.ready")
        await card.screenshot(path=out)
        await browser.close()
    print(f"{w}x{h}, {out.stat().st_size // 1024} KB -> {out}")


if __name__ == "__main__":
    width, height = (int(n) for n in sys.argv[2].split("x"))
    asyncio.run(main(Path(sys.argv[1]), width, height))
