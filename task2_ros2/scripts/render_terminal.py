#!/usr/bin/env python3
"""Render a terminal-looking PNG from plain text lines."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size: int):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render(lines: list[str], out: Path, title: str = "", width: int = 1100, pad: int = 16):
    mono = font(15)
    title_f = font(16)
    line_h = 20
    header_h = 36 if title else 0
    height = pad * 2 + header_h + max(1, len(lines)) * line_h + 8
    img = Image.new("RGB", (width, height), (18, 18, 18))
    draw = ImageDraw.Draw(img)
    if title:
        draw.rectangle((0, 0, width, header_h), fill=(40, 40, 40))
        draw.text((pad, 8), title, fill=(200, 200, 200), font=title_f)
    y = pad + header_h
    for line in lines:
        colour = (200, 200, 200)
        if "ERROR" in line or "failed" in line.lower():
            colour = (255, 120, 120)
        elif "SUMMARY" in line or "Check" in line or "passed" in line:
            colour = (120, 220, 140)
        elif "AVOID" in line or "REPLAN" in line or "PAUSED" in line or "Cone" in line:
            colour = (255, 210, 120)
        elif "Countdown" in line or "Pressed" in line or "Sent" in line:
            colour = (140, 200, 255)
        draw.text((pad, y), line[:140], fill=colour, font=mono)
        y += line_h
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"wrote {out}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out")
    p.add_argument("--title", default="")
    p.add_argument("--text", default="")
    p.add_argument("--file", default="")
    p.add_argument("--width", type=int, default=1100)
    args = p.parse_args()
    if args.file:
        lines = Path(args.file).read_text(errors="replace").splitlines()
    else:
        lines = args.text.split("\n")
    render(lines, Path(args.out), title=args.title, width=args.width)


if __name__ == "__main__":
    main()
