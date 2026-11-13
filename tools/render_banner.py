"""Render the organization profile's SVG banner and its raster fallbacks."""

import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ASSETS = Path(__file__).resolve().parents[1] / "profile" / "assets"
DURATION_MS = 9200
WIDTH, HEIGHT = 1600, 520


def snapshot(page, seconds):
    page.locator("svg").evaluate_all("(roots, t) => roots.forEach(svg => svg.setCurrentTime(t))", seconds)
    with Image.open(BytesIO(page.screenshot())) as frame:
        return frame.convert("RGB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Only render the static PNG.")
    parser.add_argument("--output-dir", type=Path, default=ASSETS)
    parser.add_argument("--browser", help="Path to an installed Chromium or Chrome executable.")
    parser.add_argument("--frames", type=int, default=230)
    args = parser.parse_args()
    if not 2 <= args.frames <= DURATION_MS // 10:
        parser.error("Choose between 2 and 920 frames for the 9.2-second GIF.")
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser)
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        page.goto((ASSETS / "banner.svg").as_uri())
        page.locator("svg").evaluate_all("roots => roots.forEach(svg => svg.pauseAnimations())")
        page.emulate_media(reduced_motion="reduce")
        snapshot(page, 0).save(output / "banner-static.png", optimize=True)
        if args.preview:
            return
        page.emulate_media(reduced_motion="no-preference")
        frames = []
        for i in range(args.frames):
            frame = snapshot(page, i * DURATION_MS / (1000 * args.frames))
            frames.append(frame.resize((1440, 468), Image.Resampling.LANCZOS))
        browser.close()

    # GIF delays are multiples of 10 ms. Preserve the SVG loop's total duration.
    ticks = [round(i * DURATION_MS / (10 * args.frames)) for i in range(args.frames + 1)]
    delays = [(end - start) * 10 for start, end in zip(ticks, ticks[1:])]
    options = dict(save_all=True, append_images=frames[1:], duration=delays, loop=0)
    frames[0].save(output / "banner.webp", lossless=True, method=4, **options)
    # A shared palette keeps the static text and card colors identical between frames.
    # Sample the fully assembled mark and preserve the deep background and gradients.
    sample = frames[round(0.27 * len(frames))]
    palette = sample.quantize(colors=256, method=Image.Quantize.MAXCOVERAGE, kmeans=1)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(output / "banner.gif", save_all=True, append_images=indexed[1:],
                    duration=delays, loop=0, disposal=1)


if __name__ == "__main__":
    main()
