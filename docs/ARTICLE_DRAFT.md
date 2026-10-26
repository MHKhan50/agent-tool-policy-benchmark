# How should AI agents be allowed to use tools? A small reproducible benchmark

## Abstract

Tool-using AI agents can propose actions that exceed the scope of a user's task. This package introduces a small synthetic benchmark comparing four policy designs: unrestricted execution, a fixed denylist, a simulated confirmation gate, and task-scoped capabilities. It reports injected-action success, acceptance of unauthorised actions, legitimate task completion, and the proportion of authorised actions blocked. The benchmark is deliberately implemented with Python's standard library so students can reproduce and extend it on a laptop.

## Research question

Under controlled synthetic workloads, what trade-offs arise between limiting unauthorised tool actions and preserving legitimate task completion?

## Motivation

Official UK university research announcements and research-degree pages show current institutional work on agent sandboxing, agent reliability/security, and agentic systems. This motivates an independent teaching benchmark; it does not establish that the specific question is novel. A literature review is required before making a novelty claim.

## Method

The simulator generates four task types and five abstract tool actions. Each task has a declared allowed-action set and required actions. Scenarios can include a missing required proposal, a benign agent error, and an injected unauthorised proposal. Four policies are evaluated across configurable random seeds. The confirmation policy assumes a configurable decision accuracy; the default 95% is a sensitivity parameter rather than a measured human-performance result. The task-scoped policy has access to the synthetic ground-truth permission set and is therefore an idealised reference.

## Results

The included run used 1,000 scenarios per seed and seeds 11, 23, and 37 (3,000 scenario evaluations per policy). The observed simulator outputs were:

- `unrestricted`: attack success **1.000** (seed-level SD 0.000); task completion **0.911** (SD 0.006); authorised-action block rate **0.000**.
- `static_denylist`: attack success **0.554** (seed-level SD 0.015); task completion **0.458** (SD 0.013); authorised-action block rate **0.331**.
- `simulated_confirmation`: attack success **0.445** (seed-level SD 0.023); task completion **0.869** (SD 0.004); authorised-action block rate **0.030**.
- `task_scoped_capability`: attack success **0.000** (seed-level SD 0.000); task completion **0.911** (SD 0.006); authorised-action block rate **0.000**.

These are actual outputs of the included code run, but they are synthetic simulation results—not real-world attack prevalence or measured performance of Qwen, Llama, Ollama, or any deployed agent. Values depend on the hand-designed task distribution, fixed policy definitions, and configured rates. The standard deviations are across the three seed-level estimates and should be treated as exploratory.

## Limitations

The action space and scenarios are hand-designed; the injection is represented as a labelled action proposal rather than raw adversarial language. No LLM, real human reviewer, operating-system sandbox, or external tool is tested. The idealised task-scoped policy is not a proof of security. The default attack/error rates are chosen parameters. Findings support only comparisons within this simulator.

## Reproducibility

The package requires Python 3.9.6 or newer and no third-party libraries. The scenario dataset is generated from a recorded seed. The code, tests, metrics, and SVG graph are intended to accompany the article.

## Conclusion

This package provides a compact, inspectable baseline for studying the security–utility trade-off in tool-using agents. The next research step is a literature-grounded extension that tests capability revocation, indirect prompt injection, policy misconfiguration, and a real local model within a safe sandbox, with preregistered metrics and repeated seeds.
