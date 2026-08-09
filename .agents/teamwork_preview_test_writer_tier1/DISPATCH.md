## 2026-08-06T03:04:00Z
You are teamwork_preview_test_writer assigned to Milestone E2E-M2: Tier 1 Feature Coverage Tests.
Your working directory is: /root/synapse/.agents/teamwork_preview_test_writer_tier1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

INSTRUCTIONS:
1. Read /root/synapse/.agents/ORIGINAL_REQUEST.md, /root/synapse/PROJECT.md, and test infra design at /root/synapse/tests/e2e/conftest.py and /root/synapse/tests/e2e/helpers.py.
2. Implement Tier 1 Feature Coverage tests (>=5 test cases per domain, marked with @pytest.mark.tier1 and @pytest.mark.e2e) in directory /root/synapse/tests/e2e/tier1/:
   - test_tier1_kernel.py (5 tests: dynamic registration, KernelInterface, health monitoring, shutdown broadcast, module tracking)
   - test_tier1_event_bus.py (5 tests: unicast routing, broadcast '*', wildcard topics, async queue handling, error isolation)
   - test_tier1_model_router.py (5 tests: GeminiFlashAdapter, OpenRouterAdapter, AntigravityAdapter, heuristic decide_model, CostTracker)
   - test_tier1_engineering.py (5 tests: EngineeringManager task execution, BackendWorker, QAWorker, DevOpsWorker, tool execution)
   - test_tier1_research.py (5 tests: ResearchManager task delegation, GitHub, HN, ProductHunt, Reddit, Twitter workers)
   - test_tier1_marketing.py (5 tests: MarketingManager campaign management, SocialWorker, ContentWorker, analytics)
   - test_tier1_sales.py (5 tests: SalesManager lead gen, OutreachWorker pitch gen, CRM tools)
   - test_tier1_personal.py (5 tests: PersonalManager assistant management, AssistantWorker task/schedule execution)
   - test_tier1_echo.py (5 tests: EchoDepartment ping/pong, payload preservation, source routing)
   - __init__.py

3. Ensure all tests use fixtures from conftest.py (fresh_kernel, harness_client, full_os_kernel) and OpaqueTestHarness.wait_for_event.
4. Execute and verify tests with: PYTHONPATH=. /root/synapse/.venv/bin/pytest tests/e2e/tier1/ -v
5. Write your report in /root/synapse/.agents/teamwork_preview_test_writer_tier1/handoff.md and send a message back.
