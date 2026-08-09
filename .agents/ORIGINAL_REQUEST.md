# Original User Request

## 2026-08-06T02:56:05Z

<USER_REQUEST>
# Teamwork Project Prompt — Draft

> Status: Ready for launch — awaiting user approval
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

Implement production-ready backend logic for the Synapse AI OS project, specifically replacing mocked stubs in the Model Router and all Departments with actual functional code.

Working directory: /root/synapse
Integrity mode: development

## Requirements

### R1. Replace Mocks with Production Logic
Remove all hardcoded mock responses (e.g., `"mocked engineering manager result"`) in the Model Router and all Departments (Engineering, Research, Marketing, Sales, Personal, Echo). Implement actual logic for handling tasks.

### R2. Adhere to Architecture
Ensure the new implementations correctly interact with the Synapse Event Bus, Kernel, and models as defined in `docs/architecture.md`. Agents must use standard Events to communicate.

## Acceptance Criteria

### Programmatic Verification
- [ ] A `pytest` test file must exist for every modified component (e.g., `tests/test_engineering.py`, `tests/test_marketing.py`).
- [ ] The tests must objectively verify that the components are processing data and routing events properly, rather than returning hardcoded strings.
- [ ] Running `PYTHONPATH=. ./.venv/bin/pytest` must pass with a 100% success rate on all newly added tests.

---
*Next: when approved → delegate via invoke_subagent (see Delegation Protocol)*
</USER_REQUEST>
