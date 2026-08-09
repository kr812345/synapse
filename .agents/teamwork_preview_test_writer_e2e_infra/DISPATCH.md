## 2026-08-05T21:31:40Z
You are teamwork_preview_test_writer assigned to Milestone E2E-M1: Test Runner Infrastructure & Harness Setup for Synapse AI OS.
Your working directory is: /root/synapse/.agents/teamwork_preview_test_writer_e2e_infra

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

INSTRUCTIONS & SPECIFICATIONS:
1. Read /root/synapse/.agents/ORIGINAL_REQUEST.md, /root/synapse/PROJECT.md, and the explorer findings at:
   - /root/synapse/.agents/teamwork_preview_explorer_e2e_r1_1/handoff.md
   - /root/synapse/.agents/teamwork_preview_explorer_e2e_r1_2/handoff.md
   - /root/synapse/.agents/teamwork_preview_explorer_e2e_r1_3/handoff.md

2. Create /root/synapse/pytest.ini with:
   - pythonpath = .
   - testpaths = tests
   - markers for tier1, tier2, tier3, tier4, e2e
   - filterwarnings ignoring pydantic / datetime deprecation warnings.

3. Create /root/synapse/tests/e2e/__init__.py and /root/synapse/tests/e2e/helpers.py:
   - Helper utilities, schema validation assertion functions for Event, Task, DAG, Knowledge, CostTracker payloads.

4. Create /root/synapse/tests/e2e/conftest.py:
   - Implement OpaqueTestHarness(Module) with deterministic wait_for_event(event_type, source, predicate, timeout=3.0) using asyncio.Event.
   - Fixtures: fresh_kernel, harness_client, full_os_kernel.
   - Custom pytest_terminal_summary hook to print clean Tier Coverage Statistics.

5. Create /root/synapse/run_e2e_tests.py:
   - CLI script supporting --tier [1|2|3|4|all], executing pytest with appropriate markers, calculating execution time and tier statistics.

6. Run a verification check using PYTHONPATH=. /root/synapse/.venv/bin/pytest tests/ to ensure existing tests still pass and configuration works smoothly.

7. Write your report in /root/synapse/.agents/teamwork_preview_test_writer_e2e_infra/handoff.md and send a message back.
