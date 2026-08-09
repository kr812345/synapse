## 2026-08-06T07:40:21Z
<USER_REQUEST>
You are the Sub-Orchestrator for Milestone 4: Final Integration & Tier 5 Adversarial Hardening.
Your working directory is: /root/synapse/.agents/sub_orch_m4
Main project directory: /root/synapse
Parent conversation ID: 73b72fea-f420-4d08-baf3-939db509f237

Instructions:
1. MUST read ORIGINAL_REQUEST.md at /root/synapse/.agents/ORIGINAL_REQUEST.md, PROJECT.md at /root/synapse/PROJECT.md, and TEST_READY.md at /root/synapse/TEST_READY.md.
2. Initialize your BRIEFING.md, progress.md, and SCOPE.md in /root/synapse/.agents/sub_orch_m4/.
3. Scope:
   - Phase 1: Verify 100% test pass rate across all existing unit tests and E2E test suite (Tiers 1-4).
   - Phase 2: Tier 5 Adversarial Coverage Hardening:
     - Spawn 2 Challengers (teamwork_preview_challenger) to perform white-box analysis of implementation source (models/, kernel/, events/, departments/, tools/) and existing tests to write Tier 5 adversarial stress tests in tests/e2e/tier5/test_tier5_adversarial_hardening.py (covering boundary race conditions, malformed event cascades, extreme tool payloads, and error isolation).
     - Spawn Worker (teamwork_preview_worker) to integrate Tier 5 adversarial test suite and resolve any edge-case bugs exposed by Challengers.
     - Spawn 2 Reviewers (teamwork_preview_reviewer) to audit code changes and verification output.
     - Spawn Forensic Auditor (teamwork_preview_auditor) to perform static analysis, AST verification, and runtime integrity checks.
4. Verify every gate condition (100% tests pass, Reviewers APPROVE, Challengers confirm, Forensic Auditor CLEAN).
5. Mark Milestone 4 complete in SCOPE.md and send a completion handoff message back to parent when done.
</USER_REQUEST>
