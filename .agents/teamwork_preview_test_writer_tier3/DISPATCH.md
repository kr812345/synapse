## 2026-08-05T21:34:00Z
You are teamwork_preview_test_writer assigned to Milestone E2E-M4: Tier 3 Cross-Feature Combination Tests.
Your working directory is: /root/synapse/.agents/teamwork_preview_test_writer_tier3

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

INSTRUCTIONS:
1. Read /root/synapse/.agents/ORIGINAL_REQUEST.md, /root/synapse/PROJECT.md, and test infra design at /root/synapse/tests/e2e/conftest.py and /root/synapse/tests/e2e/helpers.py.
2. Implement Tier 3 Cross-Feature Combination tests (marked with @pytest.mark.tier3 and @pytest.mark.e2e) in directory /root/synapse/tests/e2e/tier3/:
   - test_tier3_router_departments.py (4 tests: ModelRouter + EngineeringManager task routing, ModelRouter + ResearchManager LLM summarization, ModelRouter + MarketingManager post drafting, ModelRouter + SalesManager pitch generation)
   - test_tier3_eventbus_costtracker.py (3 tests: EventBus event cascade tracking token usage across multi-department execution, CostTracker cumulative financial calculation during broadcast events, CostTracker audit logging)
   - test_tier3_multi_department_cascades.py (4 tests: ResearchManager research finding -> MemoryEngine storage -> EngineeringManager consumes knowledge -> MarketingManager announces prototype; SalesManager qualifies lead -> PersonalManager schedules executive meeting -> Marketing sends follow-up; EchoDepartment ping benchmark under active EventBus background load; System Shutdown broadcast gracefully unregistering all 6 departments)
   - __init__.py

3. Ensure all tests use fixtures from conftest.py (fresh_kernel, harness_client, full_os_kernel) and OpaqueTestHarness.wait_for_event.
4. Execute and verify tests with: PYTHONPATH=. /root/synapse/.venv/bin/pytest tests/e2e/tier3/ -v
5. Write your report in /root/synapse/.agents/teamwork_preview_test_writer_tier3/handoff.md and send a message back.
