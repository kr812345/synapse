"""
Synapse AI OS — Tier 5 Adversarial Hardening Suite.
Consolidates and re-exports Tier 5 adversarial stress tests focusing on:
1. Extreme tool payloads, permission boundaries, error isolation, LLM router fallback stress (test_tier5_payloads_errors).
2. Boundary race conditions, concurrency saturation, malformed event cascades, DLQ corruption recovery (test_tier5_race_cascades).
"""

from tests.e2e.tier5.test_tier5_payloads_errors import (
    test_unauthorized_tool_execution_direct_and_event,
    test_unknown_tool_name_handling,
    test_invalid_tool_parameters_and_types,
    test_oversized_payloads_and_deep_structures,
    test_worker_execution_exception_boundary_isolation,
    test_subscriber_exception_isolation_under_broadcast_and_unicast,
    test_model_router_primary_and_secondary_adapter_failure_fallback,
    test_model_router_all_adapters_failing_catastrophic_error_isolation,
    test_model_router_empty_prompt_and_none_description_handling,
    test_cost_tracker_zero_token_negative_token_and_null_agent_edge_cases,
    test_concurrent_adversarial_payload_flooding,
    test_tool_registry_duplicate_registration_and_edge_cases,
    test_model_router_malformed_agent_and_payload_types,
)

from tests.e2e.tier5.test_tier5_race_cascades import (
    test_concurrent_push_pop_queue_saturation,
    test_rapid_module_registration_unregistration_race,
    test_concurrent_event_bus_shutdown_race,
    test_high_concurrency_topic_subscription_churn_race,
    test_concurrent_kernel_module_lookup_and_health_checks,
    test_circular_event_cascade_deep_recursion_safety,
    test_invalid_event_schema_missing_payload_keys,
    test_unroutable_destination_and_tricky_wildcard_patterns,
    test_dlq_overflow_and_corrupted_record_reprocessing,
    test_department_cascade_exception_storm_isolation,
    test_cascading_department_task_delegation_failure_recovery,
)

__all__ = [
    "test_unauthorized_tool_execution_direct_and_event",
    "test_unknown_tool_name_handling",
    "test_invalid_tool_parameters_and_types",
    "test_oversized_payloads_and_deep_structures",
    "test_worker_execution_exception_boundary_isolation",
    "test_subscriber_exception_isolation_under_broadcast_and_unicast",
    "test_model_router_primary_and_secondary_adapter_failure_fallback",
    "test_model_router_all_adapters_failing_catastrophic_error_isolation",
    "test_model_router_empty_prompt_and_none_description_handling",
    "test_cost_tracker_zero_token_negative_token_and_null_agent_edge_cases",
    "test_concurrent_adversarial_payload_flooding",
    "test_tool_registry_duplicate_registration_and_edge_cases",
    "test_model_router_malformed_agent_and_payload_types",
    "test_concurrent_push_pop_queue_saturation",
    "test_rapid_module_registration_unregistration_race",
    "test_concurrent_event_bus_shutdown_race",
    "test_high_concurrency_topic_subscription_churn_race",
    "test_concurrent_kernel_module_lookup_and_health_checks",
    "test_circular_event_cascade_deep_recursion_safety",
    "test_invalid_event_schema_missing_payload_keys",
    "test_unroutable_destination_and_tricky_wildcard_patterns",
    "test_dlq_overflow_and_corrupted_record_reprocessing",
    "test_department_cascade_exception_storm_isolation",
    "test_cascading_department_task_delegation_failure_recovery",
]
