#!/usr/bin/env python3
"""Create a dependency-free SVG figure from metrics_summary.csv."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
source = ROOT / "outputs" / "metrics_summary.csv"
target = ROOT / "outputs" / "policy_comparison.svg"
if not source.exists():
    raise SystemExit("Run python3 run_experiment.py first.")
with source.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
metrics = [
    ("attack_success_rate_mean", "Attack success rate (lower is better)"),
    ("task_completion_rate_mean", "Task completion rate (higher is better)"),
]
width, height = 980, 580
left, top, plot_w, plot_h = 300, 90, 560, 390
colors = ["#5276A7", "#D17B49", "#579A77", "#8B6FA8"]
lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="100%" height="100%" fill="white"/>',
         '<text x="40" y="40" font-size="24" font-family="Arial" fill="#222">Synthetic agent tool-policy benchmark</text>',
         '<text x="40" y="64" font-size="13" font-family="Arial" fill="#555">Mean across configured seeds; simulation only, not real-agent security performance</text>']
for panel, (metric, title) in enumerate(metrics):
    y0 = top + panel * 245
    lines.append(f'<text x="40" y="{y0}" font-size="17" font-family="Arial" fill="#222">{title}</text>')
    base_y = y0 + 185
    lines.append(f'<line x1="{left}" y1="{base_y}" x2="{left+plot_w}" y2="{base_y}" stroke="#666"/>')
    for tick in range(0, 6):
        val = tick / 5
        x = left + val * plot_w
        lines.append(f'<line x1="{x:.1f}" y1="{y0+25}" x2="{x:.1f}" y2="{base_y}" stroke="#ddd"/>')
        lines.append(f'<text x="{x:.1f}" y="{base_y+18}" text-anchor="middle" font-size="11" font-family="Arial" fill="#555">{val:.1f}</text>')
    for i, row in enumerate(rows):
        value = max(0.0, min(1.0, float(row[metric])))
        y = y0 + 35 + i * 34
        barw = value * plot_w
        label = row['policy'].replace('_', ' ')
        lines.append(f'<text x="{left-12}" y="{y+15}" text-anchor="end" font-size="12" font-family="Arial" fill="#222">{label}</text>')
        lines.append(f'<rect x="{left}" y="{y}" width="{barw:.1f}" height="22" fill="{colors[i % len(colors)]}"/>')
        lines.append(f'<text x="{left+barw+7:.1f}" y="{y+15}" font-size="12" font-family="Arial" fill="#222">{value:.3f}</text>')
lines.append('</svg>')
target.write_text('\n'.join(lines), encoding='utf-8')
print(f"Wrote {target}")
