#!/usr/bin/env python3
"""Create theme-neutral icon copies in assets/icons/neutral/.

README icons are plain <img> tags, so they can't follow GitHub's light/dark theme.
Logos that are black or very dark (GitHub, Linux, Pandas, Matplotlib, the Lucide
stroke icons) would vanish on one of the two themes, so each gets a mid-tone copy
that stays readable on both.
"""
import re
from pathlib import Path

ICONS = Path(__file__).resolve().parents[1] / "assets" / "icons"
OUT = ICONS / "neutral"
GRAY = "#8B949E"  # GitHub's own muted-foreground tone: readable on white and on #0d1117

# brand logos: {file: {old colour: new colour}}
BRAND_RECOLOR = {
    "pandas": {"#130754": "#8B7FE8"},
    "matplotlib": {"#2c2c2c": GRAY, "#11557c": "#4A8DB7"},
    "c": {"#a9bacd": "#5C7391"},
}
# single-colour Simple Icons logos get a flat fill
BRAND_FLAT = ["github", "linux"]
# Lucide stroke icons used in the skills table
LUCIDE = [
    "table-properties", "binary", "boxes", "database", "cpu", "network", "shapes",
    "component", "puzzle", "server", "hard-drive", "shield", "terminal",
]


def main():
    OUT.mkdir(exist_ok=True)
    for name, swaps in BRAND_RECOLOR.items():
        svg = (ICONS / "brands" / f"{name}.svg").read_text(encoding="utf-8")
        for old, new in swaps.items():
            assert old in svg, f"{name}: {old} not found"
            svg = svg.replace(old, new)
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    for name in BRAND_FLAT:
        svg = (ICONS / "brands" / f"{name}.svg").read_text(encoding="utf-8")
        svg = re.sub(r"<title>.*?</title>", "", svg)
        svg = svg.replace("<svg ", f'<svg fill="{GRAY}" ', 1)
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    for name in LUCIDE:
        svg = (ICONS / "lucide" / f"{name}.svg").read_text(encoding="utf-8")
        svg = re.sub(r"<!--.*?-->\s*", "", svg, flags=re.S)
        assert "currentColor" in svg
        (OUT / f"{name}.svg").write_text(svg.replace("currentColor", GRAY), encoding="utf-8")
    print(f"Wrote {len(list(OUT.glob('*.svg')))} neutral icons to {OUT}")


if __name__ == "__main__":
    main()
