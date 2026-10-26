#!/usr/bin/env python3
"""Generate a reusable synthetic scenario CSV without running all policies."""
import argparse
from pathlib import Path
from agent_policy_benchmark import generate_scenarios, write_scenarios_csv

p = argparse.ArgumentParser()
p.add_argument("--n", type=int, default=1000)
p.add_argument("--seed", type=int, default=20261026)
p.add_argument("--attack-rate", type=float, default=0.30)
p.add_argument("--error-rate", type=float, default=0.10)
p.add_argument("--output", default="data/synthetic_scenarios.csv")
a = p.parse_args()
if a.n < 1:
    p.error("--n must be at least 1")
scenarios = generate_scenarios(a.n, a.seed, a.attack_rate, a.error_rate)
out = Path(a.output)
write_scenarios_csv(scenarios, out)
print(f"Wrote {len(scenarios)} synthetic scenarios to {out}")
print("The configured rates are simulation assumptions, not empirical attack prevalence.")
