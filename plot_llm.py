#!/usr/bin/env python3
"""Bar chart of hidden instructions that got through each policy (outputs/llm_metrics.csv -> outputs/llm_attacks.svg)."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "outputs" / "llm_metrics.csv"
OUT = ROOT / "outputs" / "llm_attacks.svg"

POLICIES = [("unrestricted", "Unrestricted"), ("static_denylist", "Static denylist"),
            ("simulated_confirmation", "Simulated confirmation"),
            ("task_scoped_capability", "Action-name scope"), ("scoped_with_arguments", "Argument scope")]
GROUPS = [("llama3.1:8b", "en", "llama3.1:8b English", "#0b1530"), ("llama3.1:8b", "ru", "llama3.1:8b Roman Urdu", "#2b5ce6"),
          ("qwen2.5:3b", "en", "qwen2.5:3b English", "#35c3ff"), ("qwen2.5:3b", "ru", "qwen2.5:3b Roman Urdu", "#9aa7c2")]


def main():
    rows = [r for r in csv.DictReader(SRC.open(encoding="utf-8")) if r["condition"] == "injected"]
    val = {(r["model"], r["language"], r["policy"]): int(r["attack_accepted"]) for r in rows}
    W, H, left, top, bw, gap = 860, 470, 70, 80, 26, 44
    plot_h = 300
    y = lambda v: top + plot_h - v / 10 * plot_h
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 {} {}" font-family="Arial,sans-serif">'.format(W, H, W, H),
         '<rect width="100%" height="100%" fill="#ffffff"/>',
         '<text x="{}" y="34" font-size="19" font-weight="700" fill="#0f1830">Hidden instructions that got through, out of 10 tasks</text>'.format(left),
         '<text x="{}" y="56" font-size="13" fill="#55617c">One run per model, temperature 0. Lower is safer.</text>'.format(left)]
    for t in range(0, 11, 2):
        s.append('<line x1="{}" y1="{:.1f}" x2="{}" y2="{:.1f}" stroke="#dbe3f0"/>'.format(left, y(t), W - 20, y(t)))
        s.append('<text x="{}" y="{:.1f}" font-size="12" fill="#55617c" text-anchor="end">{}</text>'.format(left - 8, y(t) + 4, t))
    x = left + 20
    for key, label in POLICIES:
        for model, lang, _, colour in GROUPS:
            v = val.get((model, lang, key), 0)
            s.append('<rect x="{}" y="{:.1f}" width="{}" height="{:.1f}" fill="{}"/>'.format(x, y(v), bw - 3, top + plot_h - y(v), colour))
            s.append('<text x="{:.1f}" y="{:.1f}" font-size="11" fill="#0f1830" text-anchor="middle">{}</text>'.format(x + (bw - 3) / 2, y(v) - 4, v))
            x += bw
        s.append('<text x="{:.1f}" y="{}" font-size="12" fill="#0f1830" text-anchor="middle">{}</text>'.format(x - 2 * bw, top + plot_h + 20, label))
        x += gap
    lx = left
    for _, _, name, colour in GROUPS:
        s.append('<rect x="{}" y="{}" width="12" height="12" fill="{}"/>'.format(lx, H - 40, colour))
        s.append('<text x="{}" y="{}" font-size="12" fill="#0f1830">{}</text>'.format(lx + 17, H - 30, name))
        lx += 190
    s.append("</svg>")
    OUT.write_text("\n".join(s), encoding="utf-8")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
