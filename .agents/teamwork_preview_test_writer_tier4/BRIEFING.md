# BRIEFING — 2026-08-06T03:04:03Z

## Mission
Implement Tier 4 Real-World Application Scenario Tests for Synapse OS (Milestone E2E-M5).

## 🔒 My Identity
- Archetype: test_writer
- Roles: specialist, qa
- Working directory: /root/synapse/.agents/teamwork_preview_test_writer_tier4
- Original parent: ec241598-815f-4334-b640-7ba66a167bbf
- Milestone: E2E-M5 (Tier 4 Tests)

## 🔒 Key Constraints
- Must NOT modify implementation code — write/modify test code ONLY.
- Tests must be placed in `/root/synapse/tests/e2e/tier4/`.
- File structure: `test_tier4_product_release_workflow.py`, `test_tier4_full_agent_os_lifecycle.py`, `__init__.py`.
- Mark tests with `@pytest.mark.tier4` and `@pytest.mark.e2e`.
- Use fixtures from `conftest.py` (`fresh_kernel`, `harness_client`, `full_os_kernel`) and `OpaqueTestHarness.wait_for_event`.
- Execute and verify with `PYTHONPATH=. /root/synapse/.venv/bin/pytest tests/e2e/tier4/ -v`.
- DO NOT CHEAT or hardcode test results. Genuine assertions and event waiting required.

## Current Parent
- Conversation ID: ec241598-815f-4334-b640-7ba66a167bbf
- Updated: 2026-08-06T03:04:03Z

## Task Summary
- **What to build**: Tier 4 end-to-end tests for product release workflow, incident response workflow, customer onboarding workflow, full OS boot-to-teardown, high concurrency stress test, and system disaster recovery/memory persistence.
- **Success criteria**: All 6 tests in Tier 4 suite pass reliably with genuine assertions and proper asynchronous event handling.
- **Interface contracts**: `PROJECT.md`, `tests/e2e/conftest.py`, `tests/e2e/helpers.py`.
- **Code layout**: `tests/e2e/tier4/`.

## Key Decisions Made
- Initial setup completed.

## Artifact Index
- `/root/synapse/.agents/teamwork_preview_test_writer_tier4/DISPATCH.md` — Dispatch log
- `/root/synapse/.agents/teamwork_preview_test_writer_tier4/BRIEFING.md` — Agent briefing
