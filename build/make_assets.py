#!/usr/bin/env python3
"""Regenerate Even Brief brand raster assets from scratch.

Produces, in the repo root:
  - favicon-32.png       (32x32)   dark tile + gold "EB" monogram
  - apple-touch-icon.png (180x180) opaque dark tile + gold "EB"
  - og-image.png         (1200x630) dark social card with gold double-rule,
                                     white "Even Brief" wordmark, gold kicker,
                                     and a small tagline.

The vector source of truth for the icon is ``favicon.svg`` (hand-authored).
These PNGs are drawn directly with Pillow so the build has no SVG-rasteriser
dependency. Re-run any time:  python build/make_assets.py

Brand palette:
  bg     #0c0d11   panel  #15171d   gold #cda349
  ink    #f2f3f5   white  #ffffff   line #2a2e38
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

# ---- paths -----------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- palette ---------------------------------------------------------------
BG = (0x0c, 0x0d, 0x11)
BG_GRAD_TOP = (0x07, 0x08, 0x0b)   # near-black gradient top
PANEL = (0x15, 0x17, 0x1d)
GOLD = (0xcd, 0xa3, 0x49)
INK = (0xf2, 0xf3, 0xf5)
WHITE = (0xff, 0xff, 0xff)
LINE = (0x2a, 0x2e, 0x38)
MUTED = (0x9a, 0x9f, 0xa8)

# ---- font discovery (macOS system sans, with graceful fallback) -----------
_FONT_CANDIDATES = [
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    # Last resort: Pillow's bundled bitmap font, upscaled by the caller.
    return ImageFont.load_default()


def _have_truetype() -> bool:
    return any(os.path.exists(p) for p in _FONT_CANDIDATES)


def _rounded_tile(size: int, radius: int, opaque: bool) -> Image.Image:
    """Dark rounded square. Transparent corners unless ``opaque``."""
    mode = "RGB" if opaque else "RGBA"
    fill = BG if opaque else (0, 0, 0, 0)
    img = Image.new(mode, (size, size), fill)
    draw = ImageDraw.Draw(img)
    tile = BG if opaque else BG + (255,)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=tile)
    # subtle inner hairline border
    inset = max(1, round(size * 0.04))
    border = LINE if opaque else LINE + (255,)
    draw.rounded_rectangle(
        [inset, inset, size - 1 - inset, size - 1 - inset],
        radius=max(1, radius - inset),
        outline=border,
        width=max(1, round(size / 64)),
    )
    return img


def _draw_centered_text(draw, cx, cy, text, font, fill, anchor="mm"):
    draw.text((cx, cy), text, font=font, fill=fill, anchor=anchor)


def _icon(size: int, opaque: bool) -> Image.Image:
    """Render the EB icon at an arbitrary size, supersampled for crispness."""
    ss = 4  # supersample factor
    big = size * ss
    radius = round(big * 0.1875)  # 12/64
    img = _rounded_tile(big, radius, opaque)
    draw = ImageDraw.Draw(img)

    # gold double-rule (masthead motif) near the top
    rule_x0 = round(big * 0.22)
    rule_x1 = round(big * 0.78)
    r1y = round(big * 0.205)
    r1h = max(1, round(big * 0.037))
    draw.rounded_rectangle([rule_x0, r1y, rule_x1, r1y + r1h], radius=r1h // 2, fill=GOLD)
    r2y = r1y + r1h + max(1, round(big * 0.03))
    r2h = max(1, round(big * 0.019))
    draw.rounded_rectangle([rule_x0, r2y, rule_x1, r2y + r2h], radius=r2h // 2, fill=GOLD)

    # "EB" monogram, heavy sans, gold
    font = _load_font(round(big * 0.46))
    # position below the rule
    cx = big // 2
    cy = round(big * 0.63)
    draw.text((cx, cy), "EB", font=font, fill=GOLD, anchor="mm")

    img = img.resize((size, size), Image.LANCZOS)
    return img


def make_favicon_32():
    out = os.path.join(ROOT, "favicon-32.png")
    _icon(32, opaque=False).save(out)
    return out


def make_apple_touch():
    out = os.path.join(ROOT, "apple-touch-icon.png")
    # Apple touch icons must be opaque (no alpha).
    img = _icon(180, opaque=True).convert("RGB")
    img.save(out)
    return out


def _vertical_gradient(w, h, top, bottom):
    grad = Image.new("RGB", (w, h))
    px = grad.load()
    for y in range(h):
        t = y / max(1, h - 1)
        r = round(top[0] + (bottom[0] - top[0]) * t)
        g = round(top[1] + (bottom[1] - top[1]) * t)
        b = round(top[2] + (bottom[2] - top[2]) * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return grad


def make_og_image():
    out = os.path.join(ROOT, "og-image.png")
    W, H = 1200, 630
    # near-black gradient background
    img = _vertical_gradient(W, H, BG_GRAD_TOP, BG)
    draw = ImageDraw.Draw(img)

    margin = 90

    # gold double-rule near the top (masthead)
    rule_top = 120
    draw.rectangle([margin, rule_top, W - margin, rule_top + 5], fill=GOLD)
    draw.rectangle([margin, rule_top + 13, W - margin, rule_top + 16], fill=GOLD)

    # gold kicker above the rule
    kicker_font = _load_font(30)
    draw.text((margin, rule_top - 46), "INVESTIGATIVE GLOBAL EDITION",
              font=kicker_font, fill=GOLD, anchor="ls")

    # wordmark
    if _have_truetype():
        wordmark_font = _load_font(150)
    else:
        wordmark_font = _load_font(150)
    draw.text((margin, 300), "Even Brief", font=wordmark_font, fill=WHITE, anchor="ls")

    # tagline
    tag_font = _load_font(34)
    draw.text(
        (margin, 380),
        "A daily AI-compiled global briefing — fact-checked from public sources",
        font=tag_font, fill=INK, anchor="ls",
    )

    # bottom gold rule + url
    brule = H - 110
    draw.rectangle([margin, brule, W - margin, brule + 3], fill=GOLD)
    url_font = _load_font(28)
    draw.text((margin, brule + 50), "owenautosport.github.io/Even-Brief",
              font=url_font, fill=MUTED, anchor="ls")

    img.save(out)
    return out


def main():
    built = [
        make_favicon_32(),
        make_apple_touch(),
        make_og_image(),
    ]
    for path in built:
        with Image.open(path) as im:
            print(f"  {os.path.basename(path):24s} {im.size[0]}x{im.size[1]} {im.mode}")
    print("Done.")


if __name__ == "__main__":
    main()
