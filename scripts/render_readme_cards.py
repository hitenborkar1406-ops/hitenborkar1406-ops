#!/usr/bin/env python3
"""Render the profile README cards (SVG) from GitHub contribution + repo data.

Inputs : data/contributions.json, data/repos.json, assets/hero-anime.webp, assets/icons/*
Outputs: cards/*.svg, and the `?v=` cache-busters on card URLs inside README.md

Design notes
- Every card is a self-contained dark panel, so it looks the same on GitHub's
  light and dark themes. Nothing is fetched at view time (icons are embedded).
- Cards that sit side by side carry their own transparent margin, so spacing
  between them is part of the artwork instead of depending on HTML whitespace.
"""
import base64
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cards"
ICONS = ROOT / "assets" / "icons"
README = ROOT / "README.md"
DATA = ROOT / "data" / "contributions.json"
REPOS = ROOT / "data" / "repos.json"

# ── Theme ────────────────────────────────────────────────────────────────────
INK, SOFT, MUTED, DIM = "#EAF0FA", "#C5D0E2", "#93A3BC", "#64748B"
LINE, RAISED = "#243049", "#172136"
INDIGO, CYAN, EMERALD = "#8B7CFF", "#22D3EE", "#34D399"
HEAT = ["#1B2740", "#164E63", "#0E7490", "#22D3EE", "#A5F3FC"]  # level 0..4

SANS = '-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Helvetica,Arial,sans-serif'
MONO = 'ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace'

STYLE = f"text{{font-family:{SANS}}}.mono{{font-family:{MONO}}}"

DEFS = (
    f'<linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#16203A"/><stop offset="1" stop-color="#0D1322"/></linearGradient>'
    f'<linearGradient id="brand" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{INDIGO}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>'
)

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#F1E05A", "TypeScript": "#3178C6", "HTML": "#E34C26",
    "CSS": "#8B5CF6", "Jupyter Notebook": "#DA5B0B", "Shell": "#89E051", "C": "#8A94A6",
    "C++": "#F34B7D", "Java": "#B07219", "Dockerfile": "#2496ED", "Batchfile": "#C1F12E",
    "Mako": "#7E858D",
}
FALLBACK_COLORS = ["#8B7CFF", "#22D3EE", "#34D399", "#F59E0B", "#F472B6", "#60A5FA"]


# ── Small helpers ────────────────────────────────────────────────────────────
def svg(w, h, title, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title><defs>{DEFS}</defs><style>{STYLE}</style>{body}</svg>"
    )


def save(name, w, h, title, body):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(svg(w, h, title, body), encoding="utf-8")


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def t(x, y, s, size=16, fill=INK, w=400, anchor="start", mono=False, ls=0):
    """Text node."""
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    l = f' letter-spacing="{ls}"' if ls else ""
    c = ' class="mono"' if mono else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}"{a}{l}{c}>{escape(str(s))}</text>'


def tw(s, size, mono=False, bold=False):
    """Rough text width, good enough for laying out pills and chips."""
    if mono:
        return len(s) * size * 0.61
    narrow = set("iljtfI.,:;'| ")
    units = sum(0.64 if ch.isupper() else 0.62 if ch.isdigit() else 0.30 if ch in narrow else 0.56 for ch in s)
    return units * size * (1.05 if bold else 1)


def panel(w, h, r=24, x=0, y=0, glow=None):
    out = f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="{r}" fill="url(#panel)" stroke="{LINE}"/>'
    if glow:
        gx, gy, gr, color = glow
        out += (
            f'<defs><radialGradient id="glow" cx="{gx}" cy="{gy}" r="{gr}" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{color}" stop-opacity=".16"/><stop offset="1" stop-color="{color}" stop-opacity="0"/>'
            f'</radialGradient></defs><rect x="{x + 1}" y="{y + 1}" width="{w - 2}" height="{h - 2}" rx="{r}" fill="url(#glow)"/>'
        )
    return out


_uid = [0]


def _inner(raw):
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    raw = re.sub(r"<title>.*?</title>", "", raw, flags=re.S)
    return re.search(r"<svg[^>]*>(.*)</svg>", raw, re.S).group(1).strip()


def lucide(name, x, y, size, color, sw=2):
    """Stroke icon from assets/icons/lucide, drawn at (x, y) with the given size."""
    inner = _inner((ICONS / "lucide" / f"{name}.svg").read_text(encoding="utf-8"))
    return (
        f'<g transform="translate({x} {y}) scale({size / 24:.4f})" fill="none" stroke="{color}" '
        f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{inner}</g>'
    )


RECOLOR = {  # logos whose original colors disappear on a dark panel
    "pandas": {"#130754": "#B7AEF5"},
    "matplotlib": {"#2c2c2c": "#CBD5E1", "#11557c": "#5AA9D6"},
    "javascript": {"#323330": "#1F2937"},
}


def brand(name, x, y, size, fill=None):
    """Logo from assets/icons/brands. `fill` tints single-color (Simple Icons) logos."""
    raw = (ICONS / "brands" / f"{name}.svg").read_text(encoding="utf-8")
    vb = [float(v) for v in re.search(r'viewBox="([\d.\s-]+)"', raw).group(1).split()]
    inner = _inner(raw)
    for old, new in RECOLOR.get(name, {}).items():
        inner = inner.replace(old, new)
    _uid[0] += 1
    p = f"i{_uid[0]}-"  # ids must stay unique inside one SVG document
    inner = re.sub(r'id="([^"]+)"', lambda m: f'id="{p}{m.group(1)}"', inner)
    inner = re.sub(r"url\(#([^)]+)\)", lambda m: f"url(#{p}{m.group(1)})", inner)
    inner = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{p}{m.group(1)}"', inner)
    f = f' fill="{fill}"' if fill else ""
    return f'<g transform="translate({x} {y}) scale({size / max(vb[2], vb[3]):.4f})"{f}>{inner}</g>'


def top_bar(x, y, w, h, r, fill, extra=""):
    """Bar with rounded top corners only."""
    r = min(r, h, w / 2)
    return (
        f'<path d="M{x} {y + h}V{y + r}Q{x} {y} {x + r} {y}H{x + w - r}Q{x + w} {y} {x + w} {y + r}V{y + h}Z" '
        f'fill="{fill}"{extra}/>'
    )


# ── Data ─────────────────────────────────────────────────────────────────────
def flatten(data):
    days = [d for week in data.get("weeks", []) for d in week.get("contributionDays", [])]
    return sorted(days, key=lambda d: d["date"])


def activity_stats(days):
    counts = {d["date"]: int(d.get("contributionCount", 0)) for d in days}
    active = {date.fromisoformat(k) for k, v in counts.items() if v > 0}
    today = date.today()
    cursor = today if today in active else today - timedelta(days=1)
    current = 0
    while cursor in active:
        current += 1
        cursor -= timedelta(days=1)
    best = run = 0
    previous = None
    for day in sorted(active):
        run = run + 1 if previous and day == previous + timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    busiest = max(days, key=lambda d: int(d.get("contributionCount", 0)), default={"date": "—", "contributionCount": 0})
    monthly = defaultdict(int)
    for d in days:
        monthly[d["date"][:7]] += int(d.get("contributionCount", 0))
    return counts, len(active), current, best, busiest, monthly


def level_fn(values):
    """GitHub-style quartile levels over the non-zero days (0 = none, 4 = most)."""
    nz = sorted(v for v in values if v > 0)
    if not nz:
        return lambda c: 0
    q = [nz[min(len(nz) - 1, int(len(nz) * p))] for p in (0.25, 0.5, 0.75)]
    return lambda c: 0 if c <= 0 else 1 if c <= q[0] else 2 if c <= q[1] else 3 if c <= q[2] else 4


# ── Cards ────────────────────────────────────────────────────────────────────
def render_hero(total, active, best):
    photo = ROOT / "assets" / "hero-anime.webp"
    if not photo.exists():
        raise FileNotFoundError(f"Missing hero portrait image: {photo}")
    b64 = base64.b64encode(photo.read_bytes()).decode("ascii")
    W, H = 1200, 520
    px, py, ps = 836, 110, 300  # portrait

    chips, cx = "", 64
    for label in ("Full-stack", "Applied ML", "Data"):
        w = tw(label, 15, bold=True) + 36
        chips += (
            f'<rect x="{cx}" y="312" width="{w:.0f}" height="36" rx="18" fill="{RAISED}" stroke="{LINE}"/>'
            + t(cx + w / 2, 336, label, 15, SOFT, 600, "middle")
        )
        cx += w + 12

    stats = ""
    for i, (value, label) in enumerate(((f"{total:,}", "CONTRIBUTIONS · 12 MO"), (str(active), "ACTIVE DAYS"), (f"{best}", "LONGEST STREAK"))):
        x = 64 + i * 232
        stats += t(x, 446, value, 40, INK, 800) + t(x, 474, label, 13, MUTED, 400, mono=True, ls=1.5)
    for x in (280, 512):
        stats += f'<path d="M{x} 418V478" stroke="#33415F"/>'

    body = (
        f'<defs><clipPath id="hero-clip"><rect width="{W}" height="{H}" rx="28"/></clipPath>'
        f'<clipPath id="portrait-clip"><rect x="{px}" y="{py}" width="{ps}" height="{ps}" rx="26"/></clipPath>'
        f'<pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.1" fill="{MUTED}" fill-opacity=".22"/></pattern>'
        f'<radialGradient id="g1" cx="1010" cy="140" r="340" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{INDIGO}" stop-opacity=".38"/><stop offset="1" stop-color="{INDIGO}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="g2" cx="140" cy="540" r="380" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{CYAN}" stop-opacity=".16"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>'
        f'<filter id="blur" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="22"/></filter></defs>'
        f'<g clip-path="url(#hero-clip)"><rect width="{W}" height="{H}" fill="url(#panel)"/>'
        f'<rect width="{W}" height="{H}" fill="url(#dots)"/><rect width="{W}" height="{H}" fill="url(#g1)"/><rect width="{W}" height="{H}" fill="url(#g2)"/></g>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="28" fill="none" stroke="{LINE}"/>'
        f'<rect x="64" y="66" width="28" height="3" rx="1.5" fill="url(#brand)"/>'
        + t(106, 74, "HITEN BORKAR · ENGINEERING PORTFOLIO", 14, CYAN, 500, mono=True, ls=3)
        + t(64, 168, "Building systems", 52, INK, 800)
        + f'<text x="64" y="236" font-size="52" font-weight="800" fill="url(#brand)">that solve real problems.</text>'
        + t(64, 292, "Computer Science Engineer", 22, SOFT, 500)
        + chips
        + f'<path d="M64 392H760" stroke="{LINE}"/>'
        + stats
        + f'<rect x="{px}" y="{py}" width="{ps}" height="{ps}" rx="26" fill="url(#brand)" opacity=".55" filter="url(#blur)"/>'
        f'<rect x="{px - 5}" y="{py - 5}" width="{ps + 10}" height="{ps + 10}" rx="31" fill="none" stroke="url(#brand)" stroke-width="2"/>'
        f'<image x="{px}" y="{py}" width="{ps}" height="{ps}" preserveAspectRatio="xMidYMid slice" clip-path="url(#portrait-clip)" href="data:image/webp;base64,{b64}"/>'
    )
    save("hero.svg", W, H, "Hiten Borkar — Building systems that solve real problems", body)


def render_nav():
    items = [
        ("nav-portfolio.svg", "Portfolio", lambda x, y: lucide("globe", x, y, 22, CYAN)),
        ("nav-linkedin.svg", "LinkedIn", lambda x, y: brand("linkedin", x, y, 22, "#58A6FF")),
        ("nav-leetcode.svg", "LeetCode", lambda x, y: brand("leetcode", x, y, 22, "#FFA116")),
        ("nav-email.svg", "Email", lambda x, y: lucide("mail", x, y, 22, INDIGO)),
    ]
    for file, label, icon in items:
        start = 6.5 + (159 - (22 + 12 + tw(label, 16, bold=True))) / 2  # centre icon + label in the pill
        body = (
            f'<rect x="6.5" y="6.5" width="159" height="43" rx="21.5" fill="{RAISED}" stroke="{LINE}"/>'
            + icon(round(start, 1), 17)
            + t(round(start + 34, 1), 34, label, 16, INK, 600)
        )
        save(file, 172, 56, label, body)


def render_tiles():
    tiles = [
        ("build.svg", "BUILD", "Software & systems", "01", INDIGO, "code-xml"),
        ("data.svg", "DATA", "ML & analytics", "02", CYAN, "brain-circuit"),
        ("explore.svg", "EXPLORE", "Ideas & research", "03", EMERALD, "compass"),
    ]
    for file, label, subtitle, num, color, icon in tiles:
        body = (
            f'<defs><radialGradient id="tg" cx="370" cy="30" r="220" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{color}" stop-opacity=".22"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient></defs>'
            + panel(380, 190, 22, 10, 10)
            + '<rect x="11" y="11" width="378" height="188" rx="21" fill="url(#tg)"/>'
            + f'<rect x="34" y="34" width="52" height="52" rx="15" fill="{color}" fill-opacity=".14" stroke="{color}" stroke-opacity=".4"/>'
            + lucide(icon, 46, 46, 28, color)
            + t(366, 76, num, 30, DIM, 700, "end", mono=True)
            + t(34, 120, label, 14, color, 600, mono=True, ls=3)
            + t(34, 152, subtitle, 26, INK, 700)
            + t(34, 183, "Explore projects", 15, MUTED, 500)
            + lucide("arrow-up-right", 34 + tw("Explore projects", 15) + 6, 169, 18, color)
        )
        save(file, 400, 210, f"{label} — {subtitle}", body)


def render_activity(total, days_count, active, current, best, busiest, monthly):
    W, H = 1200, 448
    keys = sorted(monthly)[-12:] or [(date.today() - timedelta(days=30 * i)).strftime("%Y-%m") for i in range(11, -1, -1)]
    values = [monthly.get(k, 0) for k in keys]
    maximum = max(values) or 1
    peak = max(keys, key=lambda k: monthly.get(k, 0))
    peak_label = datetime.strptime(peak, "%Y-%m").strftime("%B %Y").upper()

    body = (
        f'<defs><linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{INDIGO}"/><stop offset="1" stop-color="#4C5BD4"/></linearGradient>'
        f'<linearGradient id="peak" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#67E8F9"/><stop offset="1" stop-color="#0891B2"/></linearGradient></defs>'
        + panel(W, H, 26, glow=(1000, 60, 380, INDIGO))
        + lucide("trending-up", 48, 38, 22, CYAN)
        + t(82, 55, "GITHUB ACTIVITY · LAST 12 MONTHS", 14, MUTED, 500, mono=True, ls=2.5)
        + t(48, 138, f"{total:,}", 72, INK, 800)
        + t(48 + tw(f"{total:,}", 72, bold=True) + 18, 138, "contributions", 28, MUTED, 500)
        + t(48, 172, f"PEAK MONTH · {peak_label}", 13, DIM, 500, mono=True, ls=2)
    )
    base, top, x0, span = 376, 206, 48, 744
    for frac in (0, 0.5, 1):
        y = base - (base - top) * frac
        dash = "" if frac == 0 else ' stroke-dasharray="3 6"'
        body += f'<path d="M{x0} {y:.1f}H{x0 + span}" stroke="{LINE}"{dash}/>'
    slot = span / 12
    for i, (key, value) in enumerate(zip(keys, values)):
        bw = 40
        x = x0 + i * slot + (slot - bw) / 2
        h = 0 if value == 0 else max(8, (base - top) * (value / maximum) ** 0.7)
        is_peak = key == peak and value > 0
        if h:
            body += top_bar(round(x, 1), round(base - h, 1), bw, round(h, 1), 9, "url(#peak)" if is_peak else "url(#bar)")
            body += t(round(x + bw / 2, 1), round(base - h - 10, 1), f"{value:,}", 16 if is_peak else 13, CYAN if is_peak else MUTED, 700 if is_peak else 400, "middle", mono=True)
        month = datetime.strptime(key, "%Y-%m")
        body += t(round(x + bw / 2, 1), 402, month.strftime("%b"), 13, MUTED, 400, "middle", mono=True)
        if i == 0 or month.month == 1:
            body += t(round(x + bw / 2, 1), 420, month.strftime("%Y"), 12, DIM, 400, "middle", mono=True)

    busy_date = busiest.get("date", "—")
    try:
        busy_date = datetime.strptime(busy_date, "%Y-%m-%d").strftime("%d %b").upper()
    except (ValueError, TypeError):
        pass
    body += f'<path d="M834 44V{H - 44}" stroke="{LINE}"/>'
    blocks = [
        ("flame", INDIGO, str(best), " days", f"LONGEST STREAK · CURRENT {current}"),
        ("calendar-check", CYAN, str(active), f" / {days_count}", "DAYS WITH A CONTRIBUTION"),
        ("zap", EMERALD, str(int(busiest.get("contributionCount", 0))), "", f"BUSIEST DAY · {busy_date}"),
    ]
    for i, (icon, color, value, unit, label) in enumerate(blocks):
        y = 52 + i * 128
        body += (
            f'<rect x="872" y="{y}" width="40" height="40" rx="12" fill="{color}" fill-opacity=".14" stroke="{color}" stroke-opacity=".4"/>'
            + lucide(icon, 881, y + 9, 22, color)
            + t(930, y + 56, value, 54, INK, 800)
            + (t(930 + tw(value, 54, bold=True) + 10, y + 56, unit, 22, MUTED, 500) if unit else "")
            + t(872, y + 88, label, 13, MUTED, 400, mono=True, ls=1.2)
        )
    save("activity.svg", W, H, "GitHub activity over the last 12 months", body)


def render_heatmap(days, total):
    W, H = 1200, 340
    if not days:
        return
    last = date.fromisoformat(days[-1]["date"])
    first = last - timedelta(days=363)
    first -= timedelta(days=(first.weekday() + 1) % 7)  # back up to a Sunday
    counts = {d["date"]: int(d.get("contributionCount", 0)) for d in days}
    level = level_fn(list(counts.values()))
    peak_day = max(counts, key=counts.get) if counts else None
    x0, y0, pitch, cell = 88, 142, 20, 16
    columns = ((last - first).days + 7) // 7

    body = (
        panel(W, H, 26, glow=(140, 330, 420, CYAN))
        + lucide("calendar-days", 48, 38, 24, CYAN)
        + t(84, 58, "Contribution calendar", 26, INK, 700)
        + t(48, 92, "LAST 52 WEEKS · REFRESHED DAILY", 13, MUTED, 400, mono=True, ls=2)
        + t(1152, 62, f"{total:,}", 40, CYAN, 800, "end")
        + t(1152, 90, "CONTRIBUTIONS", 13, MUTED, 400, "end", mono=True, ls=2)
    )

    # month labels sit above the column that contains the 1st of each month
    marks = [(0, first)]
    for offset in range((last - first).days + 1):
        d = first + timedelta(days=offset)
        if d.day == 1 and offset >= 7:
            marks.append((offset // 7, d))
    shown = []
    for col, d in marks:
        if not shown or col - shown[-1][0] >= 3:
            shown.append((col, d))
    for col, d in shown:
        body += t(x0 + col * pitch, 130, d.strftime("%b"), 13, MUTED, 400, mono=True)
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        body += t(48, y0 + row * pitch + 13, name, 12, DIM, 400, mono=True)

    peak_cell = None
    for col in range(columns):
        for row in range(7):
            day = first + timedelta(days=col * 7 + row)
            if day > last:
                continue
            key = day.isoformat()
            count = counts.get(key, 0)
            x, y = x0 + col * pitch, y0 + row * pitch
            label = f"{day.strftime('%A, %B %-d, %Y')}: {count} contribution{'' if count == 1 else 's'}"
            body += f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="4" fill="{HEAT[level(count)]}"><title>{escape(label)}</title></rect>'
            if key == peak_day and count > 0:
                peak_cell = (x, y)
    if peak_cell:
        body += f'<rect x="{peak_cell[0] - 2}" y="{peak_cell[1] - 2}" width="{cell + 4}" height="{cell + 4}" rx="6" fill="none" stroke="{INK}" stroke-width="2"/>'

    fy = 318
    if peak_day:
        pd = datetime.strptime(peak_day, "%Y-%m-%d").strftime("%d %b %Y").upper()
        body += t(48, fy, f"PEAK DAY · {pd} · {counts[peak_day]} CONTRIBUTIONS", 13, MUTED, 400, mono=True, ls=1.5)
    lx = 1152 - tw("More", 13, True) - 12 - (5 * pitch - 4)
    body += t(lx - 12, fy, "Less", 13, MUTED, 400, "end", mono=True)
    for j, color in enumerate(HEAT):
        body += f'<rect x="{lx + j * pitch}" y="{fy - 13}" width="{cell}" height="{cell}" rx="4" fill="{color}"/>'
    body += t(1152, fy, "More", 13, MUTED, 400, "end", mono=True)
    save("heatmap.svg", W, H, "GitHub contribution heatmap — last 52 weeks", body)


def render_languages(repos):
    W = 1200
    totals = defaultdict(int)
    for repo in repos.values():
        for language, amount in repo.get("languages", {}).items():
            totals[language] += int(amount)
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    grand = sum(totals.values()) or 1
    shown = ranked[:7]
    rest = sum(v for _, v in ranked[7:])
    if rest:
        shown.append(("Other", rest))

    def color(i, name):
        return LANG_COLORS.get(name) or FALLBACK_COLORS[i % len(FALLBACK_COLORS)]

    H = 288
    body = (
        panel(W, H, 26, glow=(1100, 20, 360, INDIGO))
        + lucide("code-xml", 48, 38, 22, CYAN)
        + t(82, 55, "CODE DISTRIBUTION · FEATURED PUBLIC REPOSITORIES", 14, MUTED, 500, mono=True, ls=2.5)
        + t(48, 108, "The code behind the work", 32, INK, 700)
        + t(1152, 108, str(len(totals)), 44, CYAN, 800, "end")
        + t(1152, 132, "LANGUAGES DETECTED", 13, MUTED, 400, "end", mono=True, ls=2)
    )
    if not shown:
        body += t(48, 190, "Language data will appear after the first repository sync.", 16, MUTED)
        save("languages.svg", W, H, "Programming language distribution", body)
        return

    bx, bw = 48, 1104
    body += f'<defs><clipPath id="bar-clip"><rect x="{bx}" y="150" width="{bw}" height="18" rx="9"/></clipPath></defs><g clip-path="url(#bar-clip)"><rect x="{bx}" y="150" width="{bw}" height="18" fill="{RAISED}"/>'
    cursor = bx
    for i, (name, amount) in enumerate(shown):
        w = bw * amount / grand
        body += f'<rect x="{cursor:.1f}" y="150" width="{max(w - 2, 1):.1f}" height="18" fill="{color(i, name)}"/>'
        cursor += w
    body += "</g>"

    col_w = bw / 4
    for i, (name, amount) in enumerate(shown):
        cx = bx + (i % 4) * col_w
        cy = 214 + (i // 4) * 40
        body += (
            f'<circle cx="{cx + 7:.1f}" cy="{cy - 5}" r="6" fill="{color(i, name)}"/>'
            + t(round(cx + 22, 1), cy, name, 16, INK, 500)
            + t(round(cx + col_w - 28, 1), cy, f"{100 * amount / grand:.1f}%", 15, MUTED, 400, "end", mono=True)
        )
    save("languages.svg", W, H, "Programming language distribution", body)


def render_repo_cards(repos):
    items = [
        ("repo-traffic.svg", "SMART_TRAFFIC_MANAGEMENT_SYSTEM", "Smart Traffic Management", "Predictive congestion and alternate routing for Nagpur.", "React · FastAPI · XGBoost · Leaflet", INDIGO),
        ("repo-ipl.svg", "IPL_CRUNCH", "IPL Crunch ’26", "Ball-by-ball IPL analytics from raw Cricsheet JSON.", "Python · Pandas · Plotly · SciPy", CYAN),
        ("repo-blindspot.svg", "PROMPTWARS", "The Blind Spot", "AI-assisted analysis of assumptions and decision biases.", "JavaScript · HTML · CSS", EMERALD),
        ("repo-rental.svg", "VEHICLE-RENTAL-SYSTEM", "Vehicle Rental System", "Flask app with booking rules and automated tests.", "Python · Flask · SQLite · pytest", "#F59E0B"),
    ]
    for i, (file, key, title, desc, stack, color) in enumerate(items, 1):
        data = repos.get(key, {})
        stars, forks = int(data.get("stargazers_count", 0)), int(data.get("forks_count", 0))
        try:
            updated = datetime.fromisoformat(data.get("updated_at", "").replace("Z", "+00:00")).strftime("%b %Y")
        except (ValueError, TypeError, AttributeError):
            updated = "—"
        ox, oy = 10, 10  # card origin inside the canvas (the margin is the gap between cards)
        body = (
            f'<defs><radialGradient id="rg" cx="560" cy="20" r="260" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{color}" stop-opacity=".18"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient></defs>'
            + panel(580, 216, 22, ox, oy)
            + f'<rect x="{ox + 1}" y="{oy + 1}" width="578" height="214" rx="21" fill="url(#rg)"/>'
            + f'<rect x="{ox + 24}" y="{oy + 22}" width="46" height="46" rx="14" fill="{color}" fill-opacity=".14" stroke="{color}" stroke-opacity=".4"/>'
            + lucide("folder-git-2", ox + 35, oy + 33, 24, color)
            + t(ox + 556, oy + 52, f"FEATURED · {i:02d}", 13, DIM, 500, "end", mono=True, ls=2)
            + t(ox + 24, oy + 104, title, 28, INK, 700)
            + t(ox + 24, oy + 130, desc, 16, MUTED, 400)
        )
        cx = ox + 24
        for tech in stack.split(" · "):
            w = tw(tech, 13, bold=True) + 24
            body += (
                f'<rect x="{cx:.0f}" y="{oy + 146}" width="{w:.0f}" height="28" rx="14" fill="{RAISED}" stroke="{LINE}"/>'
                + t(round(cx + w / 2), oy + 165, tech, 13, SOFT, 600, "middle")
            )
            cx += w + 8
        fy = oy + 200
        sx = ox + 24
        body += lucide("star", sx, fy - 14, 16, "#F59E0B") + t(sx + 22, fy, stars, 14, SOFT, 600, mono=True)
        fx = sx + 22 + tw(str(stars), 14, True) + 22
        body += lucide("git-fork", fx, fy - 14, 16, MUTED) + t(fx + 22, fy, forks, 14, SOFT, 600, mono=True)
        ux = fx + 22 + tw(str(forks), 14, True) + 22
        body += lucide("clock", ux, fy - 14, 16, MUTED) + t(ux + 22, fy, f"Updated {updated}", 14, MUTED, 400)
        save(file, 600, 236, title, body)


SKILL_GROUPS = [
    ("LANGUAGES", "code-xml", INDIGO, [
        ("C", "brand", "c"), ("C++", "brand", "cplusplus"), ("Python", "brand", "python"),
        ("Java", "brand", "java"), ("JavaScript", "brand", "javascript"), ("SQL", "lucide", "table-properties"),
    ]),
    ("WEB DEVELOPMENT", "monitor", CYAN, [("HTML5", "brand", "html5"), ("CSS3", "brand", "css3")]),
    ("ML & DATA", "brain-circuit", EMERALD, [("Pandas", "brand", "pandas"), ("NumPy", "brand", "numpy"), ("Matplotlib", "brand", "matplotlib")]),
    ("CS FUNDAMENTALS", "graduation-cap", INDIGO, [
        ("DSA", "lucide", "binary"), ("OOP", "lucide", "boxes"), ("DBMS", "lucide", "database"),
        ("Operating Systems", "lucide", "cpu"), ("Computer Networks", "lucide", "network"),
    ]),
    ("DESIGN & TOOLS", "wrench", CYAN, [
        ("UML", "lucide", "shapes"), ("OOD", "lucide", "component"), ("GoF Design Patterns", "lucide", "puzzle"),
        ("Git", "brand", "git"), ("GitHub", "mono", "github"), ("Linux", "mono", "linux"), ("VS Code", "brand", "vscode"),
    ]),
    ("CLOUD · GOOGLE CLOUD", "cloud", EMERALD, [
        ("Google Cloud", "brand", "googlecloud"), ("Compute Engine", "lucide", "server"),
        ("Cloud Storage", "lucide", "hard-drive"), ("VPC", "lucide", "shield"), ("Cloud Shell", "lucide", "terminal"),
    ]),
]


def render_skills():
    W, pad, cols, gap = 1200, 48, 3, 28
    col_w = (W - 2 * pad - gap * (cols - 1)) / cols
    chip_h, chip_gap = 42, 10
    layouts = []
    for title, icon, color, skills in SKILL_GROUPS:
        x, y, rows, row = 0.0, 0.0, [], []
        for label, kind, name in skills:
            w = 16 + 22 + 10 + tw(label, 15, bold=True) + 18
            if x and x + w > col_w:
                x, y = 0.0, y + chip_h + chip_gap
            row.append((x, y, w, label, kind, name))
            x += w + chip_gap
        layouts.append((title, icon, color, row, y + chip_h))

    row_heights = []
    for r in range(0, len(layouts), cols):
        row_heights.append(44 + max(h for *_, h in layouts[r:r + cols]))
    top, between = 40, 34
    H = top + sum(row_heights) + between * (len(row_heights) - 1) + 34

    body = panel(W, H, 26, glow=(80, 40, 380, INDIGO))
    y_cursor = top
    for ri, r in enumerate(range(0, len(layouts), cols)):
        for ci, (title, icon, color, chips, _) in enumerate(layouts[r:r + cols]):
            gx = pad + ci * (col_w + gap)
            body += lucide(icon, gx, y_cursor - 2, 20, color) + t(gx + 30, y_cursor + 14, title, 14, color, 600, mono=True, ls=2.5)
            body += f'<path d="M{gx:.0f} {y_cursor + 30}H{gx + col_w:.0f}" stroke="{LINE}"/>'
            for (cx, cy, w, label, kind, name) in chips:
                x, y = gx + cx, y_cursor + 44 + cy
                body += f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{chip_h}" rx="12" fill="{RAISED}" stroke="{LINE}"/>'
                ix, iy = x + 14, y + (chip_h - 22) / 2
                if kind == "brand":
                    body += brand(name, round(ix, 1), round(iy, 1), 22)
                elif kind == "mono":
                    body += brand(name, round(ix, 1), round(iy, 1), 22, SOFT)
                else:
                    body += lucide(name, round(ix, 1), round(iy, 1), 22, color)
                body += t(round(x + 14 + 22 + 10, 1), round(y + chip_h / 2 + 5.5, 1), label, 15, INK, 600)
        y_cursor += row_heights[ri] + between
        if ri < len(row_heights) - 1:
            body += f'<path d="M{pad} {y_cursor - between / 2:.0f}H{W - pad}" stroke="{LINE}" stroke-dasharray="2 6"/>'
    save("skills.svg", W, int(H), "Technical skills", body)


def refresh_readme_versions(version):
    """Bump the ?v= cache-buster on card URLs so GitHub's image proxy refetches them."""
    if not README.exists():
        return
    text = README.read_text(encoding="utf-8")
    new = re.sub(r"(cards/[\w-]+\.svg)\?v=[\w-]+", rf"\1?v={version}", text)
    if new != text:
        README.write_text(new, encoding="utf-8")


def main():
    contrib = read_json(DATA, {"total": 0, "weeks": []})
    days = flatten(contrib)
    counts, active, current, best, busiest, monthly = activity_stats(days)
    total = int(contrib.get("total", sum(counts.values())))
    repos = read_json(REPOS, {})

    render_hero(total, active, best)
    render_nav()
    render_tiles()
    render_activity(total, len(days), active, current, best, busiest, monthly)
    render_heatmap(days, total)
    render_repo_cards(repos)
    render_languages(repos)
    render_skills()

    version = (days[-1]["date"] if days else date.today().isoformat()).replace("-", "")
    refresh_readme_versions(version)
    print(f"Rendered profile cards: {len(days)} contribution days, {total} contributions, {len(repos)} repositories.")


if __name__ == "__main__":
    main()
