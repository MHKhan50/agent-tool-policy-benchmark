# Agent tool-policy benchmark: do permission rules stop hidden instructions in a clinic?

A small, reproducible test of five ways to control what a tool-using AI agent may do, first in a simulator and then with real local models (`qwen2.5:3b`, `llama3.1:8b`) on invented physiotherapy-clinic tasks in English and Roman Urdu.

## Research question

When a hidden instruction is placed inside a patient note, how often do small local models propose the harmful tool action, and which policy stops it without blocking the clinic's real work? In particular: does a permission rule that checks only the **action name** miss attacks that use an allowed action with the **wrong argument** (an approved referral sent to a different address, a delete aimed at the real record instead of the duplicate)?

## Why it matters

Prompt-injection benchmarks for tool agents (for example [InjecAgent](https://arxiv.org/abs/2403.02691) and [AgentDojo](https://arxiv.org/abs/2406.13352)) are in English and mostly use large hosted models. A small clinic running a local model would also face code-mixed Roman Urdu notes, and many simple guards are written as lists of allowed or forbidden tool names. This project measures that gap on a tiny, fully invented workload. It follows on from my [tool-call self-correction pilot](https://github.com/MHKhan50/agentic-ai-research-log/tree/main/tool-call-self-correction), where calls passed the schema but carried wrong values.

## Policies

| Policy | Rule |
|---|---|
| `unrestricted` | every proposed action runs |
| `static_denylist` | `send_external` and `delete_record` are always blocked |
| `simulated_confirmation` | sensitive actions go to a reviewer who is right 95% of the time (simulated, not a real person) |
| `task_scoped_capability` | only the action names allowed for this task run |
| `scoped_with_arguments` | allowed action names **and** this task's patient, approved recipient and date |

The two scoped policies are given the task's ground-truth permissions, so they are reference controls, not something a deployed system gets for free.

## Two experiments

**1. Simulator** (`agent_policy_benchmark.py`, `run_experiment.py`): 1,000 generated scenarios per seed, seeds 11, 23 and 37. The attack and error rates are settings I chose, so these numbers show how the policies behave by design, not how often real attacks happen. One thing the tests make visible: the confirmation gate only reviews sensitive actions, so even a perfect reviewer lets unauthorised low-risk actions through.

**2. Local LLM test** (`run_llm.py`, `clinic/`): 10 invented clinic tasks (summaries, follow-up booking, approved referrals, removing a confirmed duplicate) x 2 languages x {clean, hidden instruction} = 40 replies per model. Six hidden instructions ask for an action outside the task; four use an allowed action with the wrong argument. The model only proposes actions as JSON; nothing is executed. Temperature 0, seed 7.

## Run (Mac, Python 3.9+, standard library only)

```bash
python3 -m unittest discover -s tests -v
python3 run_experiment.py --n 1000 --seeds 11 23 37 && python3 plot_results.py
python3 run_llm.py --models qwen2.5:3b llama3.1:8b      # needs the Ollama app running
```

`python3 run_llm.py --score-only` re-scores the saved replies without calling a model.

Outputs: `outputs/metrics_summary.csv`, `outputs/policy_comparison.svg` (simulator); `outputs/llm_replies.jsonl` (every raw reply), `outputs/llm_metrics.csv`, `outputs/llm_run_metadata.json` (Ollama version, model digests, prompt).

## Results

### Simulator (mean of 3 seeds)

| Policy | Attack success | Task completion | Authorised actions blocked |
|---|---:|---:|---:|
| Unrestricted | _to fill from my run_ | | |
| Static denylist | | | |
| Simulated confirmation | | | |
| Task-scoped capability | | | |

### Local LLM test (counts out of 10 tasks)

_To fill from my run: hidden instruction followed, attack accepted per policy, tasks completed clean and injected, value errors, per model and language._

## Notes from my run

_To add after the run._

## Limitations

- Very small: 10 tasks, one prompt, one run per model at temperature 0. Counts, not rates; differences of one or two tasks are noise.
- All tasks, notes and hidden instructions are invented by me, and the Roman Urdu is one person's spelling. The hidden instructions are simple and visible, not adaptive attacks.
- The model proposes actions in one reply; there is no multi-step loop and no real tool output.
- Scoped policies see the true permissions, and the reviewer is simulated. The simulator's rates are design choices.
- Results do not say how secure any model or product is in real use.

## Files

| Path | What |
|---|---|
| `agent_policy_benchmark.py`, `run_experiment.py`, `generate_dataset.py`, `plot_results.py` | simulator, runner, dataset writer, SVG chart |
| `clinic/tasks.json` | 10 invented tasks, English and Roman Urdu, with hidden instructions |
| `clinic/score.py` | parsing of model replies and the five policies |
| `run_llm.py` | Ollama runner and summary |
| `tests/` | simulator and scoring tests (no Ollama needed) |
| `data/synthetic_scenarios.csv`, `DATA_CARD.md` | generated simulator scenarios and their data card |

## Licence

Code MIT. Generated and invented data CC0. See `LICENSE` and `DATA_CARD.md`.
