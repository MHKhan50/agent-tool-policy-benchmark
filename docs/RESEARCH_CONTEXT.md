# Research-context scan — 26 October 2026

This topic was selected because several official UK university pages document active work on AI-agent security, reliability, tool constraints, and agentic workflows. This establishes institutional research interest, not proof that every sub-question is novel or universally “hot”. The benchmark question below is an independent, small reproducibility proposal and is not copied from, affiliated with, or endorsed by any institution.

## Official UK sources checked

1. **University of Surrey, 15 October 2026:** announced the £3.2m Agentic-seL4 project to develop a controlled sandbox for AI agents, including changing/removing permissions and testing agent-escape scenarios. This is the freshest direct evidence motivating a lightweight policy-enforcement benchmark.
   - https://www.surrey.ac.uk/news/surrey-leads-ps32m-project-collaboration-sheffield-and-melbourne-develop-provably-secure-sandbox-ai
2. **Bournemouth University, 17 February 2026:** describes FRAME, an EU-funded project focused on the reliability, trustworthiness, security, and engineering/testing of AI agents under incomplete or uncertain information.
   - https://www.bournemouth.ac.uk/news/2026-02-17/bu-receives-over-500000-improve-ai-agents-reliability
3. **Lancaster University, current funded-PhD listing checked 26 October 2026:** lists AI-agent-security studentships and identifies prompt injection, data leakage, guardrail bypass, agent hijacking, and related risks. The listing states Home-fee eligibility and shows an October 2026 start with the deadline field marked open; because the listed start month has arrived/passed, verify directly with Lancaster before treating this as a live vacancy. This is not an assessment of any individual applicant and should not be treated as an opportunity open to everyone.
   - https://www.lancaster.ac.uk/scc/study/phd/phd-opportunities/
4. **University of Essex, MSc by Dissertation in Artificial Intelligence (current page lists October 2027 start):** lists explainable AI, generative AI, analytics/data science, NLP, and theoretical/applied AI as research supervision areas.
   - https://www.essex.ac.uk/courses/PR01632/2/MSc-by-Dissertation-Artificial-Intelligence
5. **University of Essex, MSc by Dissertation in Computer Science (current page lists January 2027 start):** includes artificial intelligence and software agents among research supervision areas.
   - https://www.essex.ac.uk/courses/PR00887/3/MSc--by-Dissertation--Computer-Science
6. **University of Portsmouth, BSc Computer Science (Artificial Intelligence), current page lists 2027 entry options:** describes a final-year independent project and study of intelligent agent-based systems and responsible AI. This is course-level evidence for undergraduate relevance, not a published list of specific dissertation titles.
   - https://london.port.ac.uk/london-study/courses/undergraduate/bsc-hons-computer-science-artificial-intelligence-london
7. **University of Strathclyde, agentic AI for sustainable engineering design PhD page:** describes benchmarking agentic LLM workflows against existing methods using performance, sustainability, and safety metrics. The listed deadline was 31 July 2026, so this is topic-context evidence, not a currently open funding opportunity.
   - https://www.strath.ac.uk/studywithus/postgraduateresearchphdopportunities/engineering/designmanufacturingengineeringmanagement/agenticaiforsustainableengineeringdesign/

## Proposed independent question

In a controlled synthetic tool-use workload, how do an unrestricted executor, a fixed denylist, a simulated confirmation gate, and task-scoped capabilities trade off acceptance of unauthorised proposals against legitimate task completion?

## Narrow practical gap to investigate, not assume

A lightweight, reproducible baseline that reports both security-oriented outcomes and utility/intervention costs may be useful for dissertation projects. The existence of a gap in the literature is not established by this scan alone. Before making a novelty claim, review recent papers and benchmarks on agent tool security, prompt injection, capability-based access control, and sandbox evaluation.

## Scope decision

The package uses no LLM and no external dataset so it can run in a short MacBook session without model downloads. It evaluates policy logic in a synthetic simulator only. A follow-on dissertation can integrate a locally hosted model only after implementing a safe tool sandbox and logging exact model/version/prompt settings.
