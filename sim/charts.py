"""Dependency-free SVG charts for simulation reports (light + dark aware)."""
from __future__ import annotations

from html import escape
from typing import Dict, List, Optional

RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
        "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]

STYLE = """
<style>
  .bg { fill: #fcfcfb; }
  .ink { fill: #0b0b0b; font: 13px system-ui, -apple-system, Segoe UI, sans-serif; }
  .ink2 { fill: #52514e; font: 12px system-ui, -apple-system, Segoe UI, sans-serif; }
  .title { fill: #0b0b0b; font: 600 15px system-ui, -apple-system, Segoe UI, sans-serif; }
  .bar { fill: #2a78d6; }
  .grid { stroke: #e1e0d9; stroke-width: 1; }
  .ref { stroke: #c0392b; stroke-width: 1.5; stroke-dasharray: 5 4; }
  .reftext { fill: #c0392b; font: 12px system-ui, sans-serif; }
  .cellink-dark { fill: #ffffff; font: 11px system-ui, sans-serif; }
  .cellink-light { fill: #0b0b0b; font: 11px system-ui, sans-serif; }
  @media (prefers-color-scheme: dark) {
    .bg { fill: #1a1a19; }
    .ink, .title { fill: #f0efec; }
    .ink2 { fill: #c3c2b7; }
    .bar { fill: #3987e5; }
    .grid { stroke: #2c2c2a; }
  }
</style>
"""


def _pretty(name: str) -> str:
    return name.replace("ending_", "").replace("_", " ")


def bar_chart(title: str, shares: Dict[str, float], subtitle: str = "",
              threshold: Optional[float] = 0.30) -> str:
    """Horizontal bars of outcome shares (0..1), one bar per category."""
    labels = list(shares)
    label_w, chart_w, row_h, top = 190, 420, 26, 62
    width = label_w + chart_w + 70
    height = top + row_h * len(labels) + 30
    vmax = max(0.6, max(shares.values() or [0]) * 1.05)
    x = lambda v: label_w + chart_w * v / vmax  # noqa: E731
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
           STYLE, f'<rect class="bg" width="{width}" height="{height}"/>',
           f'<text class="title" x="16" y="24">{escape(title)}</text>',
           f'<text class="ink2" x="16" y="44">{escape(subtitle)}</text>']
    for tick in [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        if tick > vmax:
            break
        out.append(f'<line class="grid" x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="{top - 6}" y2="{height - 26}"/>')
        out.append(f'<text class="ink2" x="{x(tick):.1f}" y="{height - 10}" text-anchor="middle">{int(tick * 100)}%</text>')
    for i, label in enumerate(labels):
        v = shares[label]
        y = top + i * row_h
        w = max(0.0, x(v) - label_w)
        out.append(f'<text class="ink" x="{label_w - 8}" y="{y + 15}" text-anchor="end">{escape(_pretty(label))}</text>')
        if w > 0:
            out.append(f'<rect class="bar" x="{label_w}" y="{y + 3}" width="{w:.1f}" height="{row_h - 8}" rx="3">'
                       f'<title>{escape(_pretty(label))}: {v * 100:.1f}%</title></rect>')
        out.append(f'<text class="ink" x="{label_w + w + 6:.1f}" y="{y + 15}">{v * 100:.1f}%</text>')
    if threshold is not None and threshold <= vmax:
        out.append(f'<line class="ref" x1="{x(threshold):.1f}" x2="{x(threshold):.1f}" y1="{top - 10}" y2="{height - 26}"/>')
        out.append(f'<text class="reftext" x="{x(threshold) + 4:.1f}" y="{top - 12}">{int(threshold * 100)}% cap</text>')
    out.append("</svg>")
    return "\n".join(out)


def heatmap(title: str, rows: List[str], cols: List[str], matrix: Dict[str, Dict[str, float]],
            subtitle: str = "", row_caption: str = "table pushes", col_caption: str = "resolved ending") -> str:
    """matrix[row][col] = share (0..1). Diagonal cells are outlined."""
    cell, left, top = 58, 190, 175
    width = left + cell * len(cols) + 140
    height = top + cell * len(rows) + 20
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
           STYLE, f'<rect class="bg" width="{width}" height="{height}"/>',
           f'<text class="title" x="16" y="24">{escape(title)}</text>',
           f'<text class="ink2" x="16" y="44">{escape(subtitle)}</text>',
           f'<text class="ink2" x="16" y="{top - 8}">{escape(row_caption)} ↓ / {escape(col_caption)} →</text>']
    for j, c in enumerate(cols):
        cx = left + j * cell + cell / 2
        out.append(f'<text class="ink2" transform="translate({cx:.1f},{top - 8}) rotate(-45)">{escape(_pretty(c))}</text>')
    for i, r in enumerate(rows):
        y = top + i * cell
        out.append(f'<text class="ink" x="{left - 8}" y="{y + cell / 2 + 4:.1f}" text-anchor="end">{escape(_pretty(r))}</text>')
        for j, c in enumerate(cols):
            v = matrix.get(r, {}).get(c, 0.0)
            idx = min(len(RAMP) - 1, int(round(v * (len(RAMP) - 1))))
            fill = RAMP[idx] if v > 0 else "none"
            xx = left + j * cell
            stroke = ' stroke="#c0392b" stroke-width="2.5"' if r == c else ' stroke="#e1e0d9" stroke-width="1"'
            out.append(f'<rect x="{xx + 1}" y="{y + 1}" width="{cell - 2}" height="{cell - 2}" rx="3" fill="{fill}"{stroke}>'
                       f'<title>{escape(_pretty(r))} → {escape(_pretty(c))}: {v * 100:.1f}%</title></rect>')
            if v >= 0.005:
                ink = "cellink-dark" if idx >= 6 else "cellink-light"
                out.append(f'<text class="{ink}" x="{xx + cell / 2:.1f}" y="{y + cell / 2 + 4:.1f}" text-anchor="middle">{v * 100:.0f}%</text>')
    out.append("</svg>")
    return "\n".join(out)
