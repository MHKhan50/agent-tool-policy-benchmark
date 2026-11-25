#!/usr/bin/env python3
"""Scores outputs_v2/runs.jsonl (no model needed) and writes tables, a chart and results.json.

  python3 analysis_v2.py

Outputs in outputs_v2/: summary.csv (per model, language and prompt), policies.csv (hidden instructions
accepted under each of the five policies), by_kind.csv (out-of-scope vs wrong-argument), paired_tests.csv
(exact McNemar tests on the same tasks), results.json and datamark.png.
"""
from __future__ import annotations

import csv
import json
import random
from math import comb
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from clinic.score import POLICIES, parse_actions, score_episode
from clinic_v2.prompts import DEFENCES

ROOT = Path(__file__).resolve().parent
TASKS = ROOT / "clinic_v2" / "tasks.json"
OUT = ROOT / "outputs_v2"
RUNS = OUT / "runs.jsonl"
LANG_NAME = {"en": "English", "ru": "Roman Urdu"}
BOOT = 2000
BOOT_SEED = 42

# House colours: blue, yellow, red, light green.
BLUE, YELLOW, RED, GREEN = "#1F4E9C", "#E3A800", "#C8102E", "#5FA65A"


def load_runs(path: Path = RUNS) -> List[Dict[str, Any]]:
    rows = []
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def score_all(runs: List[Dict[str, Any]], data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One scored row per reply and policy."""
    tasks = {t["id"]: t for t in data["tasks"]}
    out = []
    for r in runs:
        task = tasks[r["task"]]
        proposals = parse_actions(r["reply"])
        cond = "injected" if r["injected"] else "clean"
        for policy in POLICIES:
            rng = random.Random("{}|{}|{}|{}|{}|{}".format(r["model"], r["task"], r["lang"], r["defence"], cond, policy))
            s = score_episode(proposals, task, bool(r["injected"]), data["approved_recipient"], policy, rng)
            s.update({"model": r["model"], "task": r["task"], "lang": r["lang"], "defence": r["defence"],
                      "condition": cond, "policy": policy, "kind": task["injection"]["kind"],
                      "task_type": task["task_type"], "error": bool(r.get("error"))})
            out.append(s)
    return out


def bootstrap_ci(values: Sequence[float], n: int = BOOT, seed: int = BOOT_SEED) -> Tuple[float, float]:
    """95% percentile interval of the mean, resampling tasks."""
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(values)
    means = sorted(sum(values[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return (means[int(0.025 * n)], means[int(0.975 * n) - 1])


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant pairs b and c."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def pick(scored: List[Dict[str, Any]], **kw: Any) -> List[Dict[str, Any]]:
    return [s for s in scored if all(s[k] == v for k, v in kw.items())]


def by_task(rows: List[Dict[str, Any]], field: str) -> Dict[str, bool]:
    return {s["task"]: bool(s[field]) for s in rows}


def summary_rows(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    groups = sorted({(s["model"], s["lang"], s["defence"]) for s in scored},
                    key=lambda g: (g[0], g[1], DEFENCES.index(g[2])))
    for model, lang, defence in groups:
        inj = pick(scored, model=model, lang=lang, defence=defence, condition="injected", policy="unrestricted")
        cln = pick(scored, model=model, lang=lang, defence=defence, condition="clean", policy="unrestricted")
        cln_arg = pick(scored, model=model, lang=lang, defence=defence, condition="clean", policy="scoped_with_arguments")
        f = [float(s["injection_followed"]) for s in inj]
        c = [float(s["completed"]) for s in cln]
        rows.append({
            "model": model, "language": LANG_NAME[lang], "prompt": defence,
            "tasks_injected": len(inj), "followed": int(sum(f)),
            "followed_pct": round(100 * sum(f) / len(f), 1) if f else "",
            "followed_ci_low": round(100 * bootstrap_ci(f)[0], 1) if f else "",
            "followed_ci_high": round(100 * bootstrap_ci(f)[1], 1) if f else "",
            "tasks_clean": len(cln), "clean_completed": int(sum(c)),
            "clean_completed_pct": round(100 * sum(c) / len(c), 1) if c else "",
            "clean_completed_ci_low": round(100 * bootstrap_ci(c)[0], 1) if c else "",
            "clean_completed_ci_high": round(100 * bootstrap_ci(c)[1], 1) if c else "",
            "clean_completed_argument_scope": sum(s["completed"] for s in cln_arg),
            "injected_task_still_completed": sum(s["completed"] for s in inj),
            "unparsed": sum(not s["parsed"] for s in inj + cln),
            "call_errors": sum(s["error"] for s in inj + cln),
            "value_errors_clean": sum(s["value_errors"] for s in cln),
        })
    return rows


def policy_rows(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    groups = sorted({(s["model"], s["lang"], s["defence"]) for s in scored},
                    key=lambda g: (g[0], g[1], DEFENCES.index(g[2])))
    for model, lang, defence in groups:
        row: Dict[str, Any] = {"model": model, "language": LANG_NAME[lang], "prompt": defence}
        for policy in POLICIES:
            inj = pick(scored, model=model, lang=lang, defence=defence, condition="injected", policy=policy)
            cln = pick(scored, model=model, lang=lang, defence=defence, condition="clean", policy=policy)
            row["attack_" + policy] = sum(s["attack_accepted"] for s in inj)
            row["clean_done_" + policy] = sum(s["completed"] for s in cln)
        rows.append(row)
    return rows


def kind_rows(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    groups = sorted({(s["model"], s["lang"], s["defence"], s["kind"]) for s in scored if s["condition"] == "injected"},
                    key=lambda g: (g[0], g[1], DEFENCES.index(g[2]), g[3]))
    for model, lang, defence, kind in groups:
        inj = pick(scored, model=model, lang=lang, defence=defence, kind=kind, condition="injected")
        un = [s for s in inj if s["policy"] == "unrestricted"]
        name = [s for s in inj if s["policy"] == "task_scoped_capability"]
        arg = [s for s in inj if s["policy"] == "scoped_with_arguments"]
        rows.append({"model": model, "language": LANG_NAME[lang], "prompt": defence, "kind": kind, "tasks": len(un),
                     "followed": sum(s["injection_followed"] for s in un),
                     "accepted_action_name_scope": sum(s["attack_accepted"] for s in name),
                     "accepted_argument_scope": sum(s["attack_accepted"] for s in arg)})
    return rows


def paired(scored: List[Dict[str, Any]], a: Dict[str, Any], b: Dict[str, Any], condition: str,
           field: str, label: str) -> Optional[Dict[str, Any]]:
    """Exact McNemar test on tasks scored under both settings a and b (unrestricted policy)."""
    xa = by_task(pick(scored, condition=condition, policy="unrestricted", **a), field)
    xb = by_task(pick(scored, condition=condition, policy="unrestricted", **b), field)
    common = sorted(set(xa) & set(xb))
    if not common:
        return None
    only_a = sum(xa[t] and not xb[t] for t in common)
    only_b = sum(xb[t] and not xa[t] for t in common)
    return {"comparison": label, "measure": field, "tasks": len(common),
            "a": sum(xa[t] for t in common), "b": sum(xb[t] for t in common),
            "only_a": only_a, "only_b": only_b, "p_mcnemar_exact": round(mcnemar_exact(only_a, only_b), 4)}


def paired_rows(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    models = sorted({s["model"] for s in scored})
    for m in models:
        for lang in ("en", "ru"):
            for cond, field in (("injected", "injection_followed"), ("clean", "completed")):
                r = paired(scored, {"model": m, "lang": lang, "defence": "plain"},
                           {"model": m, "lang": lang, "defence": "datamark"}, cond, field,
                           "{} {}: plain (a) vs datamark (b)".format(m, LANG_NAME[lang]))
                if r:
                    rows.append(r)
        for defence in DEFENCES:
            for cond, field in (("injected", "injection_followed"), ("clean", "completed")):
                r = paired(scored, {"model": m, "lang": "en", "defence": defence},
                           {"model": m, "lang": "ru", "defence": defence}, cond, field,
                           "{} {}: English (a) vs Roman Urdu (b)".format(m, defence))
                if r:
                    rows.append(r)
    return rows


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def chart(summary: List[Dict[str, Any]], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = sorted({(r["model"], r["language"]) for r in summary}, key=lambda g: (g[0], g[1] != "English"))
    look = {(r["model"], r["language"], r["prompt"]): r for r in summary}
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), dpi=200)
    panels = [("followed", "Hidden instruction followed (%)\nlower is safer"),
              ("clean_completed", "Clean tasks completed (%)\nhigher is better")]
    w = 0.38
    for ax, (field, title) in zip(axes, panels):
        for j, (defence, colour, name) in enumerate((("plain", BLUE, "Plain prompt"), ("datamark", YELLOW, "Datamarking"))):
            xs, ys, lo, hi = [], [], [], []
            for i, g in enumerate(groups):
                r = look.get((g[0], g[1], defence))
                if not r or r[field + "_pct"] == "":
                    continue
                v = float(r[field + "_pct"])
                xs.append(i + (j - 0.5) * w)
                ys.append(v)
                lo.append(v - float(r[field + "_ci_low"]))
                hi.append(float(r[field + "_ci_high"]) - v)
            ax.bar(xs, ys, w, color=colour, label=name, yerr=[lo, hi], capsize=3,
                   error_kw={"elinewidth": 1, "ecolor": "#0f1932"})
        ax.set_xticks(range(len(groups)))
        short = {"English": "EN", "Roman Urdu": "RU"}
        ax.set_xticklabels(["{}\n{}".format(m, short.get(l, l)) for m, l in groups], fontsize=8)
        ax.set_ylim(0, 105)
        ax.set_title(title, fontsize=10.5, color="#0f1932")
        ax.grid(axis="y", color="#dbe3f0")
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].legend(frameon=False, fontsize=9)
    n = max(int(r["tasks_injected"]) for r in summary)
    fig.suptitle("Datamarking against hidden instructions in clinic notes ({} tasks, temperature 0, 95% bootstrap CI; EN = English, RU = Roman Urdu)".format(n),
                 fontsize=11, color="#0f1932")
    fig.tight_layout()
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def main() -> None:
    data = json.loads(TASKS.read_text(encoding="utf-8"))
    if not RUNS.exists():
        raise SystemExit("No {} yet. Run python3 run_v2.py first.".format(RUNS))
    runs = load_runs()
    scored = score_all(runs, data)
    summary, policies, kinds, tests = summary_rows(scored), policy_rows(scored), kind_rows(scored), paired_rows(scored)
    OUT.mkdir(exist_ok=True)
    write_csv(OUT / "summary.csv", summary)
    write_csv(OUT / "policies.csv", policies)
    write_csv(OUT / "by_kind.csv", kinds)
    write_csv(OUT / "paired_tests.csv", tests)
    results = {"replies": len(runs), "bootstrap": {"resamples": BOOT, "seed": BOOT_SEED, "unit": "task"},
               "summary": summary, "policies": policies, "by_kind": kinds, "paired_tests": tests}
    (OUT / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    chart(summary, OUT / "datamark.png")

    print("{} replies scored.\n".format(len(runs)))
    print("{:13s} {:11s} {:9s} {:>15s} {:>22s} {:>15s} {:>6s}".format(
        "model", "language", "prompt", "followed", "95% CI", "clean done", "unprs"))
    for r in summary:
        print("{:13s} {:11s} {:9s} {:>7}/{:<2} {:>5}% [{:>5}, {:>5}] {:>7}/{:<2} {:>5}% {:>6}".format(
            r["model"], r["language"], r["prompt"], r["followed"], r["tasks_injected"], r["followed_pct"],
            r["followed_ci_low"], r["followed_ci_high"], r["clean_completed"], r["tasks_clean"],
            r["clean_completed_pct"], r["unparsed"]))
    print("\nHidden instructions accepted under each policy:")
    for r in policies:
        print("  {:13s} {:11s} {:9s} ".format(r["model"], r["language"], r["prompt"]) +
              "  ".join("{}={}".format(p, r["attack_" + p]) for p in POLICIES))
    print("\nPaired tests (exact McNemar):")
    for t in tests:
        print("  {:50s} {:18s} a={:<3} b={:<3} only_a={:<3} only_b={:<3} p={}".format(
            t["comparison"], t["measure"], t["a"], t["b"], t["only_a"], t["only_b"], t["p_mcnemar_exact"]))
    print("\nWrote summary.csv, policies.csv, by_kind.csv, paired_tests.csv, results.json and datamark.png in", OUT)


if __name__ == "__main__":
    main()
