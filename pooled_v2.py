#!/usr/bin/env python3
"""Pooled view of outputs_v2/runs.jsonl across models (no model needed).

  python3 pooled_v2.py

All models see the same 40 tasks, so the 160 model-task pairs are not independent: one task can be
easy or hard for every model. Pooled comparisons are therefore tested at the task level. For each task,
d = sum over models of (followed under a) - (followed under b); a sign-flip permutation test on the 40
(or fewer) task scores gives the p-value (100,000 random sign flips, seed 42), and a task-level cluster
bootstrap (2,000 resamples, seed 42) gives a 95% interval for the pooled difference a - b.
Counts by attack kind, task type and framing are also written. Output: outputs_v2/pooled.csv.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
import random
from pathlib import Path

from analysis_v2 import OUT, TASKS, load_runs, score_all

FRAMINGS = ("SYSTEM NOTICE:", "Admin:", "IT team:")


PERMUTATIONS = 100_000
BOOT = 2_000
SEED = 42


def sign_flip_p(d: list, n: int = PERMUTATIONS, seed: int = SEED) -> float:
    """Two-sided sign-flip permutation test of sum(d) = 0, with tasks as the unit."""
    rng = random.Random(seed)
    obs = abs(sum(d))
    hits = sum(1 for _ in range(n) if abs(sum(x if rng.random() < 0.5 else -x for x in d)) >= obs)
    return (hits + 1) / (n + 1)


def cluster_ci(d: list, n: int = BOOT, seed: int = SEED) -> tuple:
    """95% interval for sum(d) from resampling tasks with replacement."""
    rng = random.Random(seed)
    sums = sorted(sum(d[rng.randrange(len(d))] for _ in d) for _ in range(n))
    return sums[int(0.025 * n)], sums[int(0.975 * n) - 1]


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

    def paired(label, a_key, b_key, keep=lambda t: True):
        ids = [t for t in sorted(tasks) if keep(tasks[t])]
        d = [sum(followed[(m, t) + a_key] - followed[(m, t) + b_key] for m in models) for t in ids]
        a = sum(followed[(m, t) + a_key] for m in models for t in ids)
        b = sum(followed[(m, t) + b_key] for m in models for t in ids)
        lo, hi = cluster_ci(d)
        out.append({"comparison": label, "tasks": len(ids), "pairs": len(ids) * len(models), "a": a, "b": b,
                    "diff_ci_low": lo, "diff_ci_high": hi, "p": "{:.2g}".format(sign_flip_p(d))})

    kind = lambda k: (lambda t: t["injection"]["kind"] == k)
    frame = lambda f: (lambda t: framing(t) == f)
    paired("English: plain (a) vs datamark (b)", ("en", "plain"), ("en", "datamark"))
    paired("Roman Urdu: plain (a) vs datamark (b)", ("ru", "plain"), ("ru", "datamark"))
    paired("plain: English (a) vs Roman Urdu (b)", ("en", "plain"), ("ru", "plain"))
    paired("datamark: English (a) vs Roman Urdu (b)", ("en", "datamark"), ("ru", "datamark"))
    for k in ("out_of_scope", "wrong_argument"):
        paired("{}, plain: English (a) vs Roman Urdu (b)".format(k), ("en", "plain"), ("ru", "plain"), kind(k))
        paired("{}, datamark: English (a) vs Roman Urdu (b)".format(k), ("en", "datamark"), ("ru", "datamark"), kind(k))
    for f in ("SYSTEM NOTICE", "Admin", "IT team", "none"):
        paired("framing {}, plain: English (a) vs Roman Urdu (b)".format(f), ("en", "plain"), ("ru", "plain"), frame(f))
        paired("framing {}, datamark: English (a) vs Roman Urdu (b)".format(f), ("en", "datamark"), ("ru", "datamark"), frame(f))

    groups = Counter()
    totals = Counter()
    for s in rows:
        t = tasks[s["task"]]
        for name, value in (("kind", s["kind"]), ("task_type", s["task_type"]), ("framing", framing(t))):
            k = (name, value, s["lang"], s["defence"])
            groups[k] += int(s["injection_followed"])
            totals[k] += 1
    for k in sorted(totals):
        out.append({"comparison": "{}={} {} {}".format(*k), "tasks": "", "pairs": totals[k], "a": groups[k],
                    "b": "", "diff_ci_low": "", "diff_ci_high": "", "p": ""})

    path = OUT / "pooled.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["comparison", "tasks", "pairs", "a", "b", "diff_ci_low", "diff_ci_high", "p"])
        w.writeheader()
        w.writerows(out)
    print("Models pooled:", ", ".join(models))
    for r in out:
        ci = "[{diff_ci_low}, {diff_ci_high}]".format(**r) if r["p"] != "" else ""
        print("{:62s} tasks={:<3} a={:<4} b={:<4} a-b 95% CI {:12s} p={}".format(r["comparison"], r["tasks"], r["a"], r["b"], ci, r["p"]))
    print("\nWrote", path)


if __name__ == "__main__":
    main()
