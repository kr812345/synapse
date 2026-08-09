## 2026-08-06T03:04:00Z
<USER_REQUEST>
You are teamwork_preview_test_writer assigned to Milestone E2E-M3: Tier 2 Boundary & Corner Case Tests.
Your working directory is: /root/synapse/.agents/teamwork_preview_test_writer_tier2

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

INSTRUCTIONS:
1. Read /root/synapse/.agents/ORIGINAL_REQUEST.md, /root/synapse/PROJECT.md, and test infra design at /root/synapse/tests/e2e/conftest.py and /root/synapse/tests/e2e/helpers.py.
2. Implement Tier 2 Boundary & Corner Case tests (>=5 test cases per domain, marked with @pytest.mark.tier2 and @pytest.mark.e2e) in directory /root/synapse/tests/e2e/tier2/:
   - test_tier2_kernel.py (5 tests: duplicate module registration, unregistering modules, empty payload broadcasting, concurrent module registrations, kernel reference injection failure edge cases)
   - test_tier2_event_bus.py (5 tests: dead-letter queue routing on unknown destination, invalid/malformed event schema validation errors, exception handling in subscriber without blocking others, circular event prevention, high volume async queue overflow handling)
   - test_tier2_model_router.py (5 tests: adapter API error failover to backup tier, empty prompt handling, unknown agent contracts, zero-token cost calculation edge cases, malformed execution request schemas)
   - test_tier2_engineering.py (5 tests: unauthorized tool invocation raising PermissionDenied, invalid task payload handling, worker execution error recovery, empty code artifact handling, invalid tool permissions)
   - test_tier2_research.py (5 tests: worker network timeout/error handling, empty search results aggregation, malformed query handling, invalid knowledge category storage, missing research sources)
   - test_tier2_marketing.py (5 tests: invalid target channel handling, empty campaign budget/specs, unauthorized social tool execution, long post truncation edge cases, missing content templates)
   - test_tier2_sales.py (5 tests: un-qualified lead handling, empty company details, missing CRM fields, outreach email template errors, zero lead score handling)
   - test_tier2_personal.py (5 tests: conflicting schedule slots, invalid datetime inputs, missing contact permissions, empty assistant tasks, invalid finance payload handling)
   - test_tier2_echo.py (5 tests: empty ping payload, nested dictionary ping payload, rapid succession pings, broadcast ping rejection, invalid destination ping)
   - __init__.py

3. Ensure all tests use fixtures from conftest.py (fresh_kernel, harness_client, full_os_kernel) and OpaqueTestHarness.wait_for_event.
4. Execute and verify tests with: PYTHONPATH=. /root/synapse/.venv/bin/pytest tests/e2e/tier2/ -v
5. Write your report in /root/synapse/.agents/teamwork_preview_test_writer_tier2/handoff.md and send a message back.
</USER_REQUEST>
