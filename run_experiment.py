#!/usr/bin/env python3
"""Run the synthetic policy benchmark with the Python standard library only."""
import argparse
import csv
import statistics
from pathlib import Path
from agent_policy_benchmark import generate_scenarios, evaluate_policy, POLICIES, write_scenarios_csv

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
DATA = ROOT / "data"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1000, help="scenarios per evaluation seed")
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 23, 37])
    parser.add_argument("--attack-rate", type=float, default=0.30)
    parser.add_argument("--error-rate", type=float, default=0.10)
    args = parser.parse_args()
    if args.n < 1:
        parser.error("--n must be at least 1")
    OUTPUTS.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    all_rows = []
    for seed in args.seeds:
        scenarios = generate_scenarios(args.n, seed, args.attack_rate, args.error_rate)
        for policy in POLICIES:
            metrics = evaluate_policy(scenarios, policy, decision_seed=seed + 9001)
            all_rows.append({"seed": seed, "policy": policy, **metrics})
    fields = list(all_rows[0].keys())
    with (OUTPUTS / "metrics_by_seed.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(all_rows)
    metric_names = ["attack_success_rate", "unauthorized_action_acceptance_rate", "task_completion_rate", "authorized_action_block_rate", "review_rate"]
    summary = []
    for policy in POLICIES:
        rows = [r for r in all_rows if r["policy"] == policy]
        row = {"policy": policy}
        for metric in metric_names:
            values = [float(r[metric]) for r in rows]
            row[metric + "_mean"] = statistics.mean(values)
            row[metric + "_stdev"] = statistics.stdev(values) if len(values) > 1 else 0.0
        summary.append(row)
    with (OUTPUTS / "metrics_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)
    # A reusable public synthetic dataset, generated independently with a documented seed.
    dataset = generate_scenarios(args.n, 20261026, args.attack_rate, args.error_rate)
    write_scenarios_csv(dataset, DATA / "synthetic_scenarios.csv")
    print(f"Wrote {len(all_rows)} policy/seed metric rows to {OUTPUTS / 'metrics_by_seed.csv'}")
    print(f"Wrote policy summary to {OUTPUTS / 'metrics_summary.csv'}")
    print(f"Wrote {len(dataset)} synthetic scenarios to {DATA / 'synthetic_scenarios.csv'}")
    print("All scenario rates are simulated design parameters, not real-world estimates.")
    for r in summary:
        print(f"{r['policy']:25s} attack_success={r['attack_success_rate_mean']:.3f} "
              f"task_completion={r['task_completion_rate_mean']:.3f} "
              f"authorized_block={r['authorized_action_block_rate_mean']:.3f}")

if __name__ == "__main__":
    main()
