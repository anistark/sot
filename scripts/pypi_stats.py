#!/usr/bin/env python3
"""Draw sot's PyPI download stats as SVGs for the README.

The numbers come from ClickHouse's public PyPI dataset, the same one ClickPy
(https://clickpy.clickhouse.com/dashboard/sot) charts. It writes a light and a
dark image to ``images/``; the README picks one with ``<picture>``.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

PACKAGE = "sot"
ENDPOINT = "https://sql-clickhouse.clickhouse.com/?user=demo&"
IMAGES = Path(__file__).parent.parent / "images"

WIDTH, HEIGHT = 880, 500
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

# GitHub's light and dark text and border colors; bars use the validated
# series-1 blue for each surface.
THEMES = {
    "light": {
        "text": "#1f2328",
        "muted": "#59636e",
        "faint": "#818b98",
        "grid": "#d1d9e0",
        "bar": "#2a78d6",
    },
    "dark": {
        "text": "#f0f6fc",
        "muted": "#9198a1",
        "faint": "#6e7681",
        "grid": "#3d444d",
        "bar": "#3987e5",
    },
}

SYSTEMS = {"Darwin": "macOS"}


def query(sql: str) -> list[dict]:
    url = ENDPOINT + urllib.parse.urlencode({"query": f"{sql} FORMAT JSON"})
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)["data"]


def collect() -> dict:
    where = f"project = '{PACKAGE}'"
    totals = query(
        "SELECT sum(count) AS total, sumIf(count, date > today() - 30) AS month "
        f"FROM pypi.pypi_downloads_per_day WHERE {where}"
    )[0]
    months = query(
        "SELECT toStartOfMonth(date) AS m, sum(count) AS n "
        f"FROM pypi.pypi_downloads_per_day WHERE {where} "
        "AND date < toStartOfMonth(today()) GROUP BY m ORDER BY m"
    )
    systems = query(
        "SELECT system AS k, sum(count) AS n "
        f"FROM pypi.pypi_downloads_per_day_by_version_by_system WHERE {where} "
        "AND system != '' GROUP BY k ORDER BY n DESC"
    )
    pythons = query(
        "SELECT python_minor AS k, sum(count) AS n "
        f"FROM pypi.pypi_downloads_per_day_by_version_by_python WHERE {where} "
        "AND python_minor != '' GROUP BY k ORDER BY n DESC"
    )
    countries = query(
        "SELECT c.name AS k, sum(d.count) AS n "
        "FROM pypi.pypi_downloads_per_day_by_version_by_country AS d "
        "LEFT JOIN pypi.countries AS c ON c.code = d.country_code "
        f"WHERE d.{where} AND d.country_code != '' GROUP BY k ORDER BY n DESC"
    )
    return {
        "total": int(totals["total"]),
        "month": int(totals["month"]),
        "months": [(date.fromisoformat(r["m"]), int(r["n"])) for r in months],
        "systems": [(SYSTEMS.get(r["k"], r["k"]), int(r["n"])) for r in systems],
        "pythons": [(r["k"], int(r["n"])) for r in pythons],
        "countries": [(r["k"], int(r["n"])) for r in countries],
    }


def compact(n: float) -> str:
    return f"{n / 1000:.1f}k" if n >= 1000 else f"{n:,.0f}"


def shares(rows: list[tuple[str, int]], top: int) -> list[tuple[str, float]]:
    """The ``top`` biggest as fractions of all rows, the rest folded into Other."""
    total = sum(n for _, n in rows) or 1
    head = [(k, n / total) for k, n in rows[:top]]
    rest = sum(n for _, n in rows[top:])
    if rest:
        head.append(("Other", rest / total))
    return head


def column(x: float, base: float, w: float, h: float, r: float = 4) -> str:
    """A bar rounded at its data end and square at the baseline."""
    r = min(r, h, w / 2)
    top = base - h
    return (
        f"M{x:.1f},{base:.1f}V{top + r:.1f}Q{x:.1f},{top:.1f} {x + r:.1f},{top:.1f}"
        f"H{x + w - r:.1f}Q{x + w:.1f},{top:.1f} {x + w:.1f},{top + r:.1f}V{base:.1f}Z"
    )


def row(x: float, y: float, w: float, h: float, r: float = 4) -> str:
    """A horizontal bar rounded at its data end."""
    r = min(r, w, h / 2)
    end = x + w
    return (
        f"M{x:.1f},{y:.1f}H{end - r:.1f}Q{end:.1f},{y:.1f} {end:.1f},{y + r:.1f}"
        f"V{y + h - r:.1f}Q{end:.1f},{y + h:.1f} {end - r:.1f},{y + h:.1f}H{x:.1f}Z"
    )


def nice_step(peak: float) -> int:
    for step in (100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000):
        if peak / step <= 4:
            return step
    return 100000


def text(x, y, s, size=12, fill="muted", anchor="start", weight=400) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
        f'fill="var(--{fill})" text-anchor="{anchor}">{escape(str(s))}</text>'
    )


def render(stats: dict, colors: dict[str, str]) -> str:
    out = []
    # Headline numbers.
    tiles = [
        ("Downloads, all time", f"{stats['total']:,}"),
        ("Last 30 days", f"{stats['month']:,}"),
        ("Countries", str(len(stats["countries"]))),
    ]
    for i, (label, value) in enumerate(tiles):
        x = 24 + i * 200
        out.append(text(x, 30, label, 13))
        out.append(text(x, 62, value, 28, "text", weight=600))

    # Downloads per month: one series, so no legend; the peak is labelled.
    months = stats["months"]
    left, right, top, base = 56, WIDTH - 24, 118, 300
    out.append(text(24, 100, "Downloads per month", 13, "text", weight=600))
    peak = max(n for _, n in months)
    step = nice_step(peak)
    ceiling = step * -(-peak // step)
    for tick in range(0, ceiling + 1, step):
        y = base - (base - top) * tick / ceiling
        out.append(
            f'<line x1="{left}" x2="{right}" y1="{y:.1f}" y2="{y:.1f}" '
            f'stroke="var(--grid)" stroke-width="1"/>'
        )
        out.append(text(left - 8, y + 4, compact(tick), 11, "faint", "end"))
    slot = (right - left) / len(months)
    bar = min(24.0, slot - 6)
    for i, (month, n) in enumerate(months):
        x = left + i * slot + (slot - bar) / 2
        h = (base - top) * n / ceiling
        label = f"{month:%b %Y}: {n:,} downloads"
        out.append(
            f'<path d="{column(x, base, bar, h)}" fill="var(--bar)">'
            f"<title>{escape(label)}</title></path>"
        )
        if n == peak:
            out.append(text(x + bar / 2, base - h - 6, f"{n:,}", 11, "text", "middle"))
        if month.month in (1, 7) or i == 0:
            name = f"{month:%b}" if month.month != 1 and i else f"{month:%b %Y}"
            out.append(text(x + bar / 2, base + 18, name, 11, "faint", "middle"))

    # Shares: platform and Python only count installs that report them.
    panels = [
        ("Platform", shares(stats["systems"], 3)),
        ("Python", shares(stats["pythons"], 4)),
        ("Top countries", shares(stats["countries"], 4)),
    ]
    width = (WIDTH - 48 - 2 * 32) / 3
    for p, (title, items) in enumerate(panels):
        x0 = 24 + p * (width + 32)
        out.append(text(x0, 356, title, 13, "text", weight=600))
        label_w, value_w = 92, 44
        track = width - label_w - value_w
        biggest = max(f for _, f in items)
        for i, (name, frac) in enumerate(items):
            y = 372 + i * 20
            out.append(text(x0, y + 10, name, 12))
            w = max(2.0, track * frac / biggest)
            out.append(
                f'<path d="{row(x0 + label_w, y, w, 12)}" fill="var(--bar)">'
                f"<title>{escape(f'{name}: {frac:.1%}')}</title></path>"
            )
            pct = f"{frac:.0%}" if frac >= 0.005 else "<1%"
            out.append(text(x0 + width, y + 10, pct, 12, "text", "end"))

    out.append(
        text(
            24,
            HEIGHT - 10,
            "Platform and Python count the installs that report them (pip, uv…); "
            f"mirrors don't. Data: ClickPy, {date.today():%d %b %Y}.",
            11,
            "faint",
        )
    )

    body = "\n".join(out)
    # Plain hex rather than CSS variables, which not every SVG renderer
    # resolves inside presentation attributes.
    for name, value in colors.items():
        body = body.replace(f"var(--{name})", value)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONT}" '
        f'role="img" aria-label="sot PyPI downloads: {stats["total"]:,} in total">\n'
        f"{body}\n</svg>\n"
    )


def main() -> None:
    stats = collect()
    for mode, colors in THEMES.items():
        path = IMAGES / f"pypi-stats-{mode}.svg"
        path.write_text(render(stats, colors))
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
