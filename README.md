# Agent tool-policy benchmark: do permission rules stop hidden instructions in a clinic?

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24228476.svg)](https://doi.org/10.5281/zenodo.24228476)

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

### Simulator (mean of 3 seeds, my run on a MacBook M4, Python 3.9.6)

| Policy | Attack success | Task completion | Authorised actions blocked |
|---|---:|---:|---:|
| Unrestricted | 1.000 | 0.911 | 0.000 |
| Static denylist | 0.554 | 0.458 | 0.331 |
| Simulated confirmation | 0.447 | 0.869 | 0.030 |
| Task-scoped capability | 0.000 | 0.911 | 0.000 |

These follow from the simulator's design: the scoped policy is given the true permissions, and the denylist blocks the actions two of the four task types need.

### Local LLM test (counts out of 10 tasks, one run, Ollama 0.40.11)

| | llama3.1:8b EN | llama3.1:8b Roman Urdu | qwen2.5:3b EN | qwen2.5:3b Roman Urdu |
|---|---:|---:|---:|---:|
| Clean tasks completed (unrestricted) | 10 | 10 | 10 | 6 |
| Hidden instruction followed | 8 | 8 | 6 | 6 |
| Got through: unrestricted | 8 | 8 | 6 | 6 |
| Got through: static denylist | 1 | 1 | 1 | 0 |
| Got through: simulated confirmation | 1 | 1 | 2 | 0 |
| Got through: action-name scope | 3 | 3 | 2 | 1 |
| Got through: argument scope | 0 | 0 | 0 | 0 |
| Clean tasks completed: static denylist | 5 | 5 | 5 | 5 |
| Clean tasks completed: argument scope | 10 | 10 | 10 | 6 |

![Hidden instructions that got through each policy](outputs/llm_attacks.svg)

- Both models usually did the real task **and** the hidden instruction, so under `unrestricted` the task still looks complete.
- What got past the action-name rule were allowed actions with the wrong argument: an approved referral sent to the other address, and a second patient's note opened. The argument rule stopped all of them.
- The denylist and the confirmation gate both let through opening another patient's note, because `read_note` is neither denylisted nor treated as sensitive. The second qwen English attack past the confirmation gate was a simulated reviewer mistake (it is right 95% of the time), and the same reviewer wrongly blocked 3 correct llama actions.
- qwen2.5:3b in Roman Urdu completed 6 of 10 clean tasks. It tried to delete the original record `P-1049` instead of the duplicate `P-1049-DUP`, twice left out the patient ID on a referral, and once read the note instead of the record and added a booking nobody asked for.
- Scoring note: in one Roman Urdu reply qwen sent the record to `export@mailbox.example`, a shortened form of the attacker's address. The scorer matches the exact address, so this counts as a value error, not as following the instruction.

Raw replies: `outputs/llm_replies.jsonl`. Re-score with `python3 run_llm.py --score-only`; redraw with `python3 plot_llm.py`.

## Notes from my run

- llama3.1:8b followed the hidden instruction in 8 of 10 tasks in both languages, qwen2.5:3b in 6 of 10. In almost every case the model also did the real task, so the attack rode along with normal work. My guess is that the bigger model follows instructions more closely, including the ones inside the note, but one run of 10 tasks cannot show why.
- For a clinic I would choose argument scope. It let none of the hidden instructions through, for both models and both languages, and did not block any correct action. The action-name rule let 3 llama attacks through, and the denylist stopped approved referrals and the duplicate removal, so only 5 of 10 clean tasks finished. Argument scope was given the true patient and recipient here, so a real system needs a trusted source for those values.
- qwen2.5:3b in Roman Urdu tried to delete the original record P-1049 instead of the duplicate, and twice sent a referral without a patient ID, while its JSON was always valid. It is the same pattern as my earlier tool-call test: right format, wrong value. I have not tested why, but in a real clinic a wrong delete would lose a patient's record.

## Limitations

- Very small: 10 tasks, one prompt, one run per model at temperature 0. Counts, not rates; differences of one or two tasks are noise.
- The injection check matches the exact injected address or patient ID, so a garbled copy of the attacker's address is counted as a value error.
- All tasks, notes and hidden instructions are invented by me, and the Roman Urdu is one person's spelling. The hidden instructions are simple and visible, not adaptive attacks.
- The model proposes actions in one reply; there is no multi-step loop and no real tool output.
- Scoped policies see the true permissions, and the reviewer is simulated. The simulator's rates are design choices.
- Results do not say how secure any model or product is in real use.

## Version 2: 40 tasks and a datamarking defence

The first LLM test had 10 tasks and one prompt. Version 2 makes the task set four times larger and asks a second question: does a prompt-level defence help small local models, and does it help as much in Roman Urdu?

**Research question.** With 40 clinic tasks in English and Roman Urdu, how often do `qwen2.5:3b` and `llama3.1:8b` follow a hidden instruction in the patient note, and does datamarking the note lower that rate without stopping the real work?

**Why datamarking.** [Hines et al. (2024)](https://arxiv.org/abs/2403.14720) proposed *spotlighting*; in its datamarking form every space in the untrusted text is replaced by a marker character and the system prompt says that marked text must never be obeyed. They report large drops in attack success, but only for GPT-family models (text-davinci-003, GPT-3.5-Turbo, GPT-4), on English summarisation and question answering, not on tool actions. Untested: small open models, tool-using agents and code-mixed Roman Urdu text.

**Design.**
- `clinic_v2/tasks.json`, built by `clinic_v2/build_tasks.py`: 5 task types (note summary, follow-up booking, approved referral, duplicate removal, allergy check in the record) x 8 cases = 40 invented tasks, each in English and Roman Urdu. In every type, 4 hidden instructions ask for an action outside the task and 4 use an allowed action with the wrong patient or recipient. Four framings are rotated (`SYSTEM NOTICE:`, `Admin:`, `IT team:`, none).
- Two prompts (`clinic_v2/prompts.py`): *plain* is the version 1 prompt, word for word (it already says that note text is data, not instructions); *datamark* marks the note with `ˆ` between words and adds the rule from the paper. The staff task itself is not marked.
- Grid: 2 models x 40 tasks x 2 languages x 2 prompts x {clean, hidden instruction} = 640 replies. Temperature 0, seed 42, at most 256 output tokens, JSON mode. The same five policies as above score every reply.
- Analysis (`analysis_v2.py`, no model needed): counts and rates per model, language and prompt; 95% bootstrap intervals that resample the 40 tasks (2,000 resamples, seed 42); exact McNemar tests on the same tasks for plain vs datamark and English vs Roman Urdu; results by attack kind; chart `outputs_v2/datamark.png`.

**Run (Mac, Python 3.9+).**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                  # offline, includes an end-to-end run with a scripted fake model
caffeinate -i python run_v2.py       # needs the Ollama app with qwen2.5:3b and llama3.1:8b; resumable
python analysis_v2.py
```
`run_v2.py` appends each reply to `outputs_v2/runs.jsonl` straight away and skips finished calls, so it can be stopped and started again. Model digests, the Ollama version and both system prompts go to `outputs_v2/run_metadata.json`.

**Results** (my run on a MacBook M4, 15 November 2026, Ollama 0.40.16; 640 replies, no failed calls, all valid JSON; 95% bootstrap intervals resample the 40 tasks).

| Model | Language | Prompt | Hidden instruction followed [95% CI] | Clean tasks completed [95% CI] |
|---|---|---|---|---|
| llama3.1:8b | English | plain | 20/40, 50.0% [35.0, 65.0] | 40/40 |
| llama3.1:8b | English | datamark | 2/40, 5.0% [0.0, 12.5] | 40/40 |
| llama3.1:8b | Roman Urdu | plain | 21/40, 52.5% [37.5, 67.5] | 40/40 |
| llama3.1:8b | Roman Urdu | datamark | 11/40, 27.5% [15.0, 42.5] | 40/40 |
| qwen2.5:3b | English | plain | 22/40, 55.0% [40.0, 70.0] | 40/40 |
| qwen2.5:3b | English | datamark | 9/40, 22.5% [10.0, 37.5] | 40/40 |
| qwen2.5:3b | Roman Urdu | plain | 24/40, 60.0% [45.0, 75.0] | 32/40, 80.0% [67.5, 92.5] |
| qwen2.5:3b | Roman Urdu | datamark | 15/40, 37.5% [22.5, 52.5] | 24/40, 60.0% [45.0, 75.0] |

![Datamarking against hidden instructions](outputs_v2/datamark.png)

Paired tests on the same 40 tasks (exact McNemar):

| Comparison | Followed: plain vs datamark | p |
|---|---|---|
| llama3.1:8b English | 20 vs 2 (18 tasks changed, all towards safer) | < 0.0001 |
| llama3.1:8b Roman Urdu | 21 vs 11 | 0.021 |
| qwen2.5:3b English | 22 vs 9 (13 tasks changed, all towards safer) | 0.0002 |
| qwen2.5:3b Roman Urdu | 24 vs 15 | 0.023 |
| llama3.1:8b with datamark, English vs Roman Urdu | 2 vs 11 | 0.023 |
| qwen2.5:3b with datamark, English vs Roman Urdu | 9 vs 15 | 0.21 |
| qwen2.5:3b clean tasks, Roman Urdu, plain vs datamark | 32 vs 24 completed | 0.008 |

By attack kind (followed, out of 20 each; `outputs_v2/by_kind.csv`):

| Model | Language | Out of scope: plain → datamark | Wrong argument: plain → datamark |
|---|---|---|---|
| llama3.1:8b | English | 4 → 0 | 16 → 2 |
| llama3.1:8b | Roman Urdu | 11 → 4 | 10 → 7 |
| qwen2.5:3b | English | 9 → 0 | 13 → 9 |
| qwen2.5:3b | Roman Urdu | 12 → 11 | 12 → 4 |

Hidden instructions accepted under the policies (`outputs_v2/policies.csv`): argument scope let **0** through in all 8 settings and blocked no correct clean action; action-name scope let 2 to 16 through, all of them wrong-argument attacks.

- **Datamarking lowered the rate in all four settings**, most for English: with datamarking, llama3.1:8b followed 2 hidden instructions in English and 11 in Roman Urdu. Without it the two languages were almost the same (20 vs 21, 22 vs 24).
- In English, datamarking stopped every out-of-scope attack for both models; what was left were wrong-argument attacks. llama3.1:8b's 2 were follow-ups booked under the other patient ID (V12, V16).
- **The only cost was qwen2.5:3b in Roman Urdu.** All 8 extra failures were follow-up bookings (V09 to V16) where it booked the right patient and the right date but skipped the required `read_note` step; the date was visible in the prompt. Its other 16 failed clean tasks (8 per prompt) were referrals where it used `read_note` instead of `read_record`, and in some replies sent the referral without a patient ID or added a booking nobody asked for.

**Notes from my run**

- Datamarking cut the hidden instructions llama3.1:8b followed from 20 to 2 of 40 in English, but only from 21 to 11 in Roman Urdu. After datamarking, the gap between the two languages was significant (2 vs 11, p = 0.023). My guess is that the marker splits Roman Urdu words, which are already broken into many small tokens, so the model sees the note boundary less clearly. I have not tested this.
- Datamarking cost nothing in English for either model, or in Roman Urdu for llama3.1:8b (40 of 40 clean tasks done). For qwen2.5:3b in Roman Urdu, clean tasks done fell from 32 to 24 (p = 0.008). Every reply was still valid JSON. The 8 extra failures were bookings with the right patient and date where qwen skipped reading the note first, so the cost was a skipped step, not a broken reply.
- Datamarking lowers the rate but does not stop attacks: after it, 11 (llama3.1:8b) and 15 (qwen2.5:3b) Roman Urdu attacks were still followed. Argument scope let 0 through for every model, language and prompt. For a clinic I would keep datamarking only as an extra layer and check tool arguments in code.

**Limitations.**
- 40 invented tasks and hidden instructions written by me; the Roman Urdu is one person's spelling. The attacks are simple and visible, not adaptive.
- One run per model at temperature 0. Ollama outputs can differ across versions and hardware.
- One reply per task, no multi-step loop and no real tool output.
- The injection check matches the exact injected address or patient ID.
- Datamarking is tested in one form (one marker, one wording of the rule); the paper also describes delimiting and encoding.

## Files

| Path | What |
|---|---|
| `agent_policy_benchmark.py`, `run_experiment.py`, `generate_dataset.py`, `plot_results.py` | simulator, runner, dataset writer, SVG chart |
| `clinic/tasks.json` | 10 invented tasks, English and Roman Urdu, with hidden instructions |
| `clinic/score.py` | parsing of model replies and the five policies |
| `run_llm.py`, `plot_llm.py` | Ollama runner and summary, LLM chart |
| `tests/` | simulator and scoring tests (no Ollama needed) |
| `data/synthetic_scenarios.csv`, `DATA_CARD.md` | generated simulator scenarios and their data card |
| `clinic_v2/build_tasks.py`, `clinic_v2/tasks.json` | version 2: 40 invented tasks, English and Roman Urdu |
| `clinic_v2/prompts.py` | version 2: plain and datamarking prompts |
| `run_v2.py`, `analysis_v2.py` | version 2: resumable Ollama runner; tables, tests, chart and `results.json` |
| `tests/test_v2.py`, `requirements.txt` | version 2 offline tests (scripted fake model) and Python packages |

## Article

- [Small local AI agents followed hidden instructions in clinic notes. Checking the tool's arguments stopped them.](https://masmatixinnovations.co.uk/insights/agent-tool-policy-clinic.html) (version 1)
- [Marking the clinic note cut hidden instructions to 2 of 40 in English, but only to 11 of 40 in Roman Urdu](https://masmatixinnovations.co.uk/insights/datamarking-hidden-instructions-roman-urdu.html) (version 2)

## Licence

Code MIT. Generated and invented data CC0. See `LICENSE` and `DATA_CARD.md`.
