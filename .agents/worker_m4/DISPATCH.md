## 2026-08-06T06:53:45Z
You are Worker for Milestone 4: Final Integration & Tier 5 Adversarial Hardening.
Your working directory is: /root/synapse/.agents/worker_m4
Main project directory: /root/synapse

Instructions:
1. MUST read ORIGINAL_REQUEST.md at /root/synapse/.agents/ORIGINAL_REQUEST.md, PROJECT.md at /root/synapse/PROJECT.md, and TEST_READY.md at /root/synapse/TEST_READY.md.
2. Read handoff reports from Challengers at /root/synapse/.agents/challenger_1_m4/handoff.md and /root/synapse/.agents/challenger_2_m4/handoff.md.
3. Integrate the Tier 5 adversarial stress test suite:
   - Verify `tests/e2e/tier5/test_tier5_adversarial_hardening.py`, `tests/e2e/tier5/test_tier5_race_cascades.py`, and `tests/e2e/tier5/test_tier5_payloads_errors.py`.
   - Ensure all Tier 5 tests covering boundary race conditions, malformed event cascades, extreme tool payloads, and error isolation are cleanly integrated, imported, and executable via `tests/e2e/tier5/test_tier5_adversarial_hardening.py`.
   - Verify that all exposed edge-case fixes (including `models/model_router.py` handling of `task_description: None` payloads) are cleanly integrated, well-structured, and fully tested.
4. Execute the test suite to verify 100% pass rate:
   - Run `PYTHONPATH=. ./.venv/bin/pytest`
   - Run `PYTHONPATH=. ./.venv/bin/python run_e2e_tests.py --tier all`
   Document the exact commands and output logs.
5. MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
6. Write a detailed handoff report in `/root/synapse/.agents/worker_m4/handoff.md` and update `progress.md`.
7. Send a message back to parent orchestrator with your integration findings, test execution results, and handoff report location.
