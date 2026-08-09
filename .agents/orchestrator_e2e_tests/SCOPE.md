# Scope: E2E Test Suite Orchestration

## Scope Overview
Deliver the complete, requirement-driven, opaque-box E2E test suite for Synapse AI OS.

## Milestones & Work Items

| # | Work Item | Description | Subagent Assignment | Status |
|---|-----------|-------------|---------------------|--------|
| E2E-M1 | Test Harness & Infra | Setup `tests/e2e/` structure, fixtures, runner script | teamwork_preview_test_writer | PLANNED |
| E2E-M2 | Tier 1 Feature Coverage | >=5 test cases per feature for Model Router, Event Bus, Kernel, and 6 Departments | teamwork_preview_test_writer | PLANNED |
| E2E-M3 | Tier 2 Boundary & Corner | >=5 test cases per feature area (edge cases, invalid data, timeouts, errors) | teamwork_preview_test_writer | PLANNED |
| E2E-M4 | Tier 3 Cross-Feature | Pairwise interaction tests across Event Bus, Router, Departments | teamwork_preview_test_writer | PLANNED |
| E2E-M5 | Tier 4 Real-World Workflows | Multi-agent end-to-end OS workflow scenarios | teamwork_preview_test_writer | PLANNED |
| E2E-M6 | Verification & Publication | Run full test suite, publish TEST_INFRA.md and TEST_READY.md | teamwork_preview_worker / reviewer | PLANNED |

## Requirements Mapping
- **Opaque-Box**: Tests interact via public APIs, Kernel interface, Event Bus envelopes, and standard event schemas without relying on internal mock hacks.
- **Minimum Count**: >=5 test cases per feature for Tier 1 and Tier 2.
- **Coverage Domains**: Kernel, Event Bus, Model Router (with adapters & cost tracker), Engineering, Research, Marketing, Sales, Personal, Echo.
