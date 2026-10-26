# Data card: synthetic agent-tool policy scenarios

## Summary

A generated, tabular collection of task scenarios, task permissions, required actions, and proposed tool actions. The dataset is intended for reproducible teaching, baseline comparisons, and small-scale methods development.

## Provenance

Generated locally by `agent_policy_benchmark.py` using Python's standard-library pseudo-random generator. Default seed: `20261026`; default size: 1,000 scenarios. Reproduce with:

```bash
python3 generate_dataset.py --n 1000 --seed 20261026 --output data/synthetic_scenarios.csv
```

No web scraping, human-subject data, user logs, proprietary content, or external dataset is used.

## Fields

- `scenario_id`: stable ID derived from seed and row index.
- `seed`: pseudo-random seed used for the scenario.
- `task_type`: one of four synthetic task types.
- `allowed_actions`: JSON array of actions permitted for the task.
- `required_actions`: JSON array of actions needed to complete the task.
- `proposals`: JSON array of proposed actions, each with `action` and `source` (`task_plan`, `agent_error`, or `injection`).

## Intended use

Teaching and research on evaluation design, policy-control trade-offs, synthetic benchmark reproducibility, and sensitivity analysis.

## Out-of-scope use

Do not use these rows to estimate real-world prompt-injection prevalence, claim measured security performance of commercial models, or make production security decisions.

## Known limitations

Scenarios and action spaces are hand-designed; there are only four task types and five actions. Injection is represented as an already-classified proposal, not raw natural-language prompt injection. No LLM, human reviewer, operating-system sandbox, or external tool is evaluated. Task-scoped capability sees the ground-truth allowed-action set.

## Licensing and attribution

Generated scenario data is intended to be CC0/public-domain-equivalent where legally possible. Code is MIT licensed. If redistributing, include this card and the version/seed/rates. Attribute the package if helpful, but no third-party dataset attribution is required.
