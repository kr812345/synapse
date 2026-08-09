## 2026-08-06T03:07:51Z
You are Explorer 2 for Milestone 2: Technical Departments (Research Focus).
Your working directory is: /root/synapse/.agents/explorer_m2_2
Main project directory: /root/synapse

MANDATORY FIRST STEP: Read the following files:
- /root/synapse/.agents/ORIGINAL_REQUEST.md
- /root/synapse/PROJECT.md
- /root/synapse/.agents/sub_orch_m2/SCOPE.md

Task Objectives:
Investigate existing code and design a detailed, complete implementation plan for the Research Department:
1. F-RES-1: Refactor `ResearchManager` (`departments/research/manager.py`)
   - Must inherit `Module` and `BaseAgent`, register with `Kernel`.
   - Remove static `delegated` stub / mock responses.
   - Parse research requests, delegate to platform workers (GitHub, HN, ProductHunt, Reddit, Twitter), aggregate results, and output research report artifacts.
2. F-RES-2: Refactor platform workers in `departments/research/workers/` (`github.py`, `hn.py`, `product_hunt.py`, `reddit.py`, `twitter.py`)
   - Perform functional query searches, process data, and return non-empty structured results (e.g. structured dicts/dataclasses containing real/simulated search query matching, topic analysis, sentiment/trending metrics).
3. F-RES-3: Design test suite structure for `tests/test_research.py`
   - Test ResearchManager kernel registration, event handling, platform worker queries, aggregation, report artifact generation, and non-mock output validation.

Write your findings, exact code signatures, architecture, and step-by-step implementation guide to `/root/synapse/.agents/explorer_m2_2/analysis.md` and write a handoff report at `/root/synapse/.agents/explorer_m2_2/handoff.md`.
Then send a completion message with summary to parent.
