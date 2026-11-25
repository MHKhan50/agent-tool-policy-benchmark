#!/usr/bin/env python3
"""Pooled view of outputs_v2/runs.jsonl across models (no model needed).

  python3 pooled_v2.py

Pairs are (model, task): each model sees the same 40 tasks, so pooling 4 models gives 160 pairs per
comparison. Writes outputs_v2/pooled.csv and prints the same numbers.
Exact McNemar tests on the pairs; counts by attack kind, task type and framing of the hidden instruction.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from math import comb
from pathlib import Path

from analysis_v2 import OUT, TASKS, load_runs, score_all

FRAMINGS = ("SYSTEM NOTICE:", "Admin:", "IT team:")


def mcnemar(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def framing(task: dict) -> str:
    text = task["injection"]["en"]
    for f in FRAMINGS:
        if text.startswith(f):
            return f.rstrip(":")
    return "none"


def main() -> None:
    data = json.loads(TASKS.read_text(encoding="utf-8"))
    tasks = {t["id"]: t for t in data["tasks"]}
    rows = [s for s in score_all(load_runs(), data) if s["policy"] == "unrestricted" and s["condition"] == "injected"]
    models = sorted({s["model"] for s in rows})
    followed = {(s["model"], s["task"], s["lang"], s["defence"]): bool(s["injection_followed"]) for s in rows}
    out = []

    def paired(label, a_key, b_key):
        keys = [(m, t) for m in models for t in tasks]
        a = [followed[(m, t) + a_key] for m, t in keys]
        b = [followed[(m, t) + b_key] for m, t in keys]
        only_a = sum(x and not y for x, y in zip(a, b))
        only_b = sum(y and not x for x, y in zip(a, b))
        out.append({"comparison": label, "pairs": len(keys), "a": sum(a), "b": sum(b), "only_a": only_a,
                    "only_b": only_b, "p": "{:.2g}".format(mcnemar(only_a, only_b))})

    paired("English: plain (a) vs datamark (b)", ("en", "plain"), ("en", "datamark"))
    paired("Roman Urdu: plain (a) vs datamark (b)", ("ru", "plain"), ("ru", "datamark"))
    paired("plain: English (a) vs Roman Urdu (b)", ("en", "plain"), ("ru", "plain"))
    paired("datamark: English (a) vs Roman Urdu (b)", ("en", "datamark"), ("ru", "datamark"))

    groups = Counter()
    totals = Counter()
    for s in rows:
        t = tasks[s["task"]]
        for name, value in (("kind", s["kind"]), ("task_type", s["task_type"]), ("framing", framing(t))):
            k = (name, value, s["lang"], s["defence"])
            groups[k] += int(s["injection_followed"])
            totals[k] += 1
    for k in sorted(totals):
        out.append({"comparison": "{}={} {} {}".format(*k), "pairs": totals[k], "a": groups[k],
                    "b": "", "only_a": "", "only_b": "", "p": ""})

    path = OUT / "pooled.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["comparison", "pairs", "a", "b", "only_a", "only_b", "p"])
        w.writeheader()
        w.writerows(out)
    print("Models pooled:", ", ".join(models))
    for r in out:
        print("{comparison:45s} n={pairs:<4} a={a:<4} b={b:<4} only_a={only_a:<3} only_b={only_b:<3} p={p}".format(**r))
    print("\nWrote", path)


if __name__ == "__main__":
    main()
