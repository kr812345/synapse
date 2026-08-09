## 2026-08-06T03:04:01Z
You are teamwork_preview_test_writer assigned to Milestone E2E-M5: Tier 4 Real-World Application Scenario Tests.
Your working directory is: /root/synapse/.agents/teamwork_preview_test_writer_tier4

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

INSTRUCTIONS:
1. Read /root/synapse/.agents/ORIGINAL_REQUEST.md, /root/synapse/PROJECT.md, and test infra design at /root/synapse/tests/e2e/conftest.py and /root/synapse/tests/e2e/helpers.py.
2. Implement Tier 4 Real-World Application Scenario tests (marked with @pytest.mark.tier4 and @pytest.mark.e2e) in directory /root/synapse/tests/e2e/tier4/:
   - test_tier4_product_release_workflow.py (3 tests: E2E Product Release Lifecycle: Research market -> Engineering build -> Marketing campaign -> Sales outreach -> Personal task logging; E2E Automated Incident Response: DevOpsWorker detects incident -> Research searches logs -> Engineering fixes -> Marketing publishes status update -> Post-mortem stored in MemoryEngine; E2E Customer Onboarding Workflow: Sales closes deal -> Personal schedules onboarding -> Engineering provisions environment -> Marketing sends welcome kit)
   - test_tier4_full_agent_os_lifecycle.py (3 tests: Full OS Boot to Graceful Teardown Lifecycle: Boot -> Register 9 modules -> Execute 20 multi-department tasks -> Verify CostTracker & MemoryEngine -> Shutdown; High Concurrency Multi-Department Stress Test: 50 concurrent tasks across all 6 departments via Scheduler & ModelRouter without message loss or queue deadlock; System Disaster Recovery & Memory Persistence: Kernel restart reloading active tasks & knowledge graph state from SQLite MemoryEngine)
   - __init__.py

3. Ensure all tests use fixtures from conftest.py (fresh_kernel, harness_client, full_os_kernel) and OpaqueTestHarness.wait_for_event.
4. Execute and verify tests with: PYTHONPATH=. /root/synapse/.venv/bin/pytest tests/e2e/tier4/ -v
5. Write your report in /root/synapse/.agents/teamwork_preview_test_writer_tier4/handoff.md and send a message back.
