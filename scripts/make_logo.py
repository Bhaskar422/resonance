"""Render the Resonance logo (the favicon's ring and dot) as square PNGs for OAuth consent screens.

The square is filled edge to edge because Google and GitHub crop logos to a circle.

    .venv/bin/python scripts/make_logo.py   # -> brand/logo-120.png, logo-512.png, logo-1024.png
"""

from pathlib import Path

from PIL import Image, ImageDraw

BG, SIGNAL = (10, 13, 12), (94, 240, 160)  # the web app's --bg and --signal
OUT = Path(__file__).resolve().parent.parent / "brand"


def logo(size: int) -> Image.Image:
    s = size * 8  # draw large, then downsample for smooth edges
    img = Image.new("RGB", (s, s), BG)
    d = ImageDraw.Draw(img)
    c, ring, width, dot = s / 2, s * 9 / 32, s * 2.4 / 32, s * 3 / 32  # favicon.svg proportions
    d.ellipse([c - ring - width / 2, c - ring - width / 2, c + ring + width / 2, c + ring + width / 2], fill=SIGNAL)
    d.ellipse([c - ring + width / 2, c - ring + width / 2, c + ring - width / 2, c + ring - width / 2], fill=BG)
    d.ellipse([c - dot, c - dot, c + dot, c + dot], fill=SIGNAL)
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for size in (120, 512, 1024):
        logo(size).save(OUT / f"logo-{size}.png", optimize=True)
        print(OUT / f"logo-{size}.png")
