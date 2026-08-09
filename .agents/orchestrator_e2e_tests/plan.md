# E2E Test Suite Orchestration Plan

## Goal
Build a comprehensive, requirement-driven, opaque-box E2E test suite for Synapse AI OS according to the Dual Track protocol in `PROJECT.md`.

## Features Under Test (9 Core Domains)
1. **Kernel (`kernel/kernel.py`)**: Registration, event routing, lifecycle hooks, health monitoring, shutdown.
2. **Event Bus (`events/event_bus.py`)**: Unicast, pub/sub broadcast (`*`), wildcards, async queues, dead-letter queue, payload validation, error boundaries.
3. **Model Router (`models/model_router.py`)**: Abstract `ModelAdapter`, Tier 1 (Gemini Flash), Tier 2 (OpenRouter), Tier 3 (Antigravity CLI), heuristic routing, fallback redundancy, `CostTracker`.
4. **Engineering Department (`departments/engineering/`)**: EngineeringManager, BackendWorker, QAWorker, DevOpsWorker.
5. **Research Department (`departments/research/`)**: ResearchManager, GitHubWorker, HNWorker, ProductHuntWorker, RedditWorker, TwitterWorker.
6. **Marketing Department (`departments/marketing/`)**: MarketingManager, SocialWorker, ContentWorker.
7. **Sales Department (`departments/sales/`)**: SalesManager, OutreachWorker / SalesWorker.
8. **Personal Department (`departments/personal/`)**: PersonalManager, AssistantWorker.
9. **Echo Department (`departments/echo/`)**: EchoDepartment ping/pong event module.

## Test Tier Architecture
- **Tier 1: Feature Coverage (>=5 test cases per feature area)**
  - Validate core happy path and feature mechanics for all 9 components.
- **Tier 2: Boundary & Corner Cases (>=5 test cases per feature area)**
  - Test limits, empty payloads, invalid destinations, high volume events, malformed requests, timeout/fallback triggers, unknown routes.
- **Tier 3: Cross-Feature Combinations (Pairwise interactions)**
  - Multi-department cascades (e.g. Research -> Engineering -> Model Router -> Kernel), broadcast events consumed by multiple departments, Event Bus + CostTracker integration.
- **Tier 4: Real-World Application Scenarios (E2E workflows)**
  - Complete agent OS workflows (e.g., product release cycle: Research market -> Engineering build -> Marketing launch -> Sales outreach -> Personal task logging).

## Phases & Deliverables
1. **Phase 1: Infra & Harness**: Establish `tests/e2e/` test harness, helper utilities, pytest configuration, runner script.
2. **Phase 2: Tier 1 & Tier 2 Test Cases**: Implement unit/integration/E2E test files for Tier 1 and Tier 2 across all 9 domains.
3. **Phase 3: Tier 3 & Tier 4 Test Cases**: Implement pairwise cross-feature tests and multi-department real-world workflow tests.
4. **Phase 4: Execution & Verification**: Run test suite via pytest runner subagent, confirm 100% pass rate.
5. **Phase 5: Documentation & Publication**: Publish `/root/synapse/TEST_INFRA.md` and `/root/synapse/TEST_READY.md`. Notify parent.
