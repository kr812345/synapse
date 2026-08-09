"""
Tier 4 Real-World Application Scenario Tests: Product Release, Incident Response, and Customer Onboarding Workflows.
"""

import pytest
import asyncio
from typing import List, Dict, Any

from shared.models import Event, Task, DAG, AgentContract, Knowledge
from tests.e2e.helpers import (
    assert_valid_event,
    assert_event_matches,
    assert_valid_task,
    assert_valid_dag,
    assert_valid_knowledge,
    assert_valid_cost_tracker_payload,
    create_test_knowledge,
    create_test_task,
    create_test_dag,
    create_test_event,
)


@pytest.mark.tier4
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_product_release_lifecycle(full_os_kernel, harness_client):
    """
    E2E Product Release Lifecycle:
    Research market -> Engineering build -> Marketing campaign -> Sales outreach -> Personal task logging.
    Verifies multi-department task DAG execution, sequential dependency unblocking, cost tracking, and MemoryEngine persistence.
    """
    # 1. Register agent contracts for 5 departments into AgentRegistry
    departments = ["research", "engineering", "marketing", "sales", "personal"]
    for dept in departments:
        agent_id = f"{dept}_agent"
        contract = AgentContract(
            identity=agent_id,
            department=dept,
            goal=f"Execute {dept} operations for product release",
            responsibilities=[f"{dept}_tasks"],
            forbidden_actions=[],
            allowed_tools=[f"{dept}_tool"],
            memory_access="department_wide",
            output_schema={},
        )
        await full_os_kernel.send_event(
            create_test_event(
                source=harness_client.name,
                destination="agent_registry",
                event_type="registry.register_agent",
                payload={"contract": contract.model_dump()},
            )
        )
        reg_ack = await harness_client.wait_for_event(
            event_type="registry.agent_registered",
            predicate=lambda e, aid=agent_id: e.payload.get("identity") == aid,
            timeout=3.0,
        )
        assert reg_ack.payload["identity"] == agent_id

    # 2. Build 5-stage sequential DAG
    t1 = create_test_task(
        description="Research market trends and feature matrix for AI OS v1.0",
        requester=harness_client.name,
    )
    t2 = create_test_task(
        description="Engineering build core AI OS kernel and API infrastructure",
        requester=harness_client.name,
        dependencies=[t1.id],
    )
    t3 = create_test_task(
        description="Marketing campaign creation and press announcement for launch",
        requester=harness_client.name,
        dependencies=[t2.id],
    )
    t4 = create_test_task(
        description="Sales outreach to tier-1 enterprise beta clients",
        requester=harness_client.name,
        dependencies=[t3.id],
    )
    t5 = create_test_task(
        description="Personal task logging and executive retrospective summary",
        requester=harness_client.name,
        dependencies=[t4.id],
    )

    for task_obj in [t1, t2, t3, t4, t5]:
        assert_valid_task(task_obj)

    dag = create_test_dag(
        name="E2E Product Release Lifecycle DAG",
        requester=harness_client.name,
        tasks=[t1, t2, t3, t4, t5],
    )
    assert_valid_dag(dag)

    # 3. Submit DAG to Scheduler
    await full_os_kernel.send_event(
        create_test_event(
            source=harness_client.name,
            destination="scheduler",
            event_type="dag.create",
            payload={"dag": dag.model_dump()},
        )
    )

    # 4. Wait for completion of each task in sequence using predicate filter
    completed_task_ids = []
    for task_obj in [t1, t2, t3, t4, t5]:
        comp_event = await harness_client.wait_for_event(
            event_type="task.complete",
            predicate=lambda e, tid=task_obj.id: e.payload.get("task_id") == tid,
            timeout=5.0,
        )
        assert_valid_event(comp_event)
        task_id = comp_event.payload["task_id"]
        completed_task_ids.append(task_id)
        assert_valid_cost_tracker_payload(comp_event.payload)

    assert completed_task_ids == [t1.id, t2.id, t3.id, t4.id, t5.id]

    dag_complete_event = await harness_client.wait_for_event(
        event_type="dag.complete",
        predicate=lambda e: e.payload.get("dag_id") == dag.id,
        timeout=5.0,
    )
    assert_event_matches(
        dag_complete_event,
        source="scheduler",
        destination=harness_client.name,
        event_type="dag.complete",
        payload_subset={"dag_id": dag.id},
    )

    # 5. Store release completion record in MemoryEngine
    release_knowledge = create_test_knowledge(
        observation="Product Release v1.0 successfully launched across Research, Engineering, Marketing, Sales, Personal.",
        source="product_release_workflow",
        category="release_milestone",
        confidence=1.0,
        importance=10,
    )
    assert_valid_knowledge(release_knowledge)

    await full_os_kernel.send_event(
        create_test_event(
            source=harness_client.name,
            destination="memory_engine",
            event_type="memory.store_knowledge",
            payload={"knowledge": release_knowledge.model_dump()},
        )
    )
    stored_ack = await harness_client.wait_for_event(
        event_type="memory.knowledge_stored",
        predicate=lambda e: e.payload.get("knowledge_id") == release_knowledge.id,
        timeout=3.0,
    )
    assert stored_ack.payload["knowledge_id"] == release_knowledge.id

    # 6. Query MemoryEngine to verify persistence
    await full_os_kernel.send_event(
        create_test_event(
            source=harness_client.name,
            destination="memory_engine",
            event_type="memory.query_knowledge",
            payload={"query": "Product Release v1.0"},
        )
    )
    query_resp = await harness_client.wait_for_event(
        event_type="memory.query_results",
        predicate=lambda e: e.payload.get("query") == "Product Release v1.0",
        timeout=3.0,
    )
    assert len(query_resp.payload["results"]) > 0
    found_obs = query_resp.payload["results"][0]["observation"]
    assert "Product Release v1.0" in found_obs

    # 7. Verify ModelRouter cost tracker metrics
    model_router = full_os_kernel.get_module("model_router")
    assert model_router is not None
    summary = model_router.cost_tracker.get_summary()
    assert summary["request_count"] >= 5
    assert summary["total_tokens"] > 0


@pytest.mark.tier4
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_automated_incident_response(full_os_kernel, harness_client):
    """
    E2E Automated Incident Response:
    DevOpsWorker detects incident -> Research searches logs -> Engineering fixes -> Marketing publishes status update -> Post-mortem stored in MemoryEngine.
    """
    # 1. Register agents for DevOps, Research, Engineering, Marketing
    agents_spec = [
        ("devops_worker", "engineering"),
        ("research_worker", "research"),
        ("backend_worker", "engineering"),
        ("marketing_worker", "marketing"),
    ]
    for identity, dept in agents_spec:
        contract = AgentContract(
            identity=identity,
            department=dept,
            goal=f"Handle incident response step for {identity}",
            responsibilities=["incident_management"],
            forbidden_actions=[],
            allowed_tools=["incident_tool"],
            memory_access="admin",
            output_schema={},
        )
        await full_os_kernel.send_event(
            create_test_event(
                source=harness_client.name,
                destination="agent_registry",
                event_type="registry.register_agent",
                payload={"contract": contract.model_dump()},
            )
        )
        await harness_client.wait_for_event(
            event_type="registry.agent_registered",
            predicate=lambda e, aid=identity: e.payload.get("identity") == aid,
            timeout=3.0,
        )

    # 2. Trigger incident event from system broadcast
    incident_event = create_test_event(
        source="system_monitor",
        destination="*",
        event_type="incident.detected",
        payload={
            "incident_id": "INC-8809",
            "severity": "CRITICAL",
            "service": "k8s-cluster-auth",
            "error_rate": "15.4%",
            "timestamp": "2026-08-06T03:00:00Z",
        },
    )
    await full_os_kernel.send_event(incident_event)
    detected_evt = await harness_client.wait_for_event(
        event_type="incident.detected",
        source="system_monitor",
        predicate=lambda e: e.payload.get("incident_id") == "INC-8809",
        timeout=3.0,
    )
    assert_event_matches(detected_evt, event_type="incident.detected", source="system_monitor")

    # 3. Create incident response DAG
    t1 = create_test_task(
        description="DevOpsWorker detects incident INC-8809 and captures stack trace metrics",
        requester=harness_client.name,
    )
    t2 = create_test_task(
        description="Research department searches system logs and telemetry for root cause",
        requester=harness_client.name,
        dependencies=[t1.id],
    )
    t3 = create_test_task(
        description="Engineering department fixes auth memory leak and deploys hotfix v1.0.4",
        requester=harness_client.name,
        dependencies=[t2.id],
    )
    t4 = create_test_task(
        description="Marketing department publishes status page update regarding INC-8809 resolution",
        requester=harness_client.name,
        dependencies=[t3.id],
    )

    for task_obj in [t1, t2, t3, t4]:
        assert_valid_task(task_obj)

    incident_dag = create_test_dag(
        name="Automated Incident Response Workflow",
        requester=harness_client.name,
        tasks=[t1, t2, t3, t4],
    )
    assert_valid_dag(incident_dag)

    await full_os_kernel.send_event(
        create_test_event(
            source=harness_client.name,
            destination="scheduler",
            event_type="dag.create",
            payload={"dag": incident_dag.model_dump()},
        )
    )

    # 4. Wait for all incident resolution tasks to complete in order
    completed_task_ids = []
    for task_obj in [t1, t2, t3, t4]:
        comp_evt = await harness_client.wait_for_event(
            event_type="task.complete",
            predicate=lambda e, tid=task_obj.id: e.payload.get("task_id") == tid,
            timeout=5.0,
        )
        completed_task_ids.append(comp_evt.payload["task_id"])
        assert_valid_cost_tracker_payload(comp_evt.payload)

    assert completed_task_ids == [t1.id, t2.id, t3.id, t4.id]

    dag_ack = await harness_client.wait_for_event(
        event_type="dag.complete",
        predicate=lambda e: e.payload.get("dag_id") == incident_dag.id,
        timeout=5.0,
    )
    assert dag_ack.payload["dag_id"] == incident_dag.id

    # 5. Store Incident Post-Mortem in MemoryEngine
    post_mortem = create_test_knowledge(
        observation="Post-Mortem INC-8809: Auth memory leak in worker pool fixed by hotfix v1.0.4. Zero data loss.",
        source="incident_response_team",
        category="post_mortem",
        confidence=1.0,
        importance=9,
    )
    assert_valid_knowledge(post_mortem)

    await full_os_kernel.send_event(
        create_test_event(
            source=harness_client.name,
            destination="memory_engine",
            event_type="memory.store_knowledge",
            payload={"knowledge": post_mortem.model_dump()},
        )
    )
    await harness_client.wait_for_event(
        event_type="memory.knowledge_stored",
        predicate=lambda e: e.payload.get("knowledge_id") == post_mortem.id,
        timeout=3.0,
    )

    # 6. Verify Post-Mortem retrieval
    await full_os_kernel.send_event(
        create_test_event(
            source=harness_client.name,
            destination="memory_engine",
            event_type="memory.query_knowledge",
            payload={"query": "INC-8809"},
        )
    )
    res_evt = await harness_client.wait_for_event(
        event_type="memory.query_results",
        predicate=lambda e: e.payload.get("query") == "INC-8809",
        timeout=3.0,
    )
    assert len(res_evt.payload["results"]) > 0
    assert "INC-8809" in res_evt.payload["results"][0]["observation"]


@pytest.mark.tier4
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_customer_onboarding_workflow(full_os_kernel, harness_client):
    """
    E2E Customer Onboarding Workflow:
    Sales closes deal -> Personal schedules onboarding -> Engineering provisions environment -> Marketing sends welcome kit.
    """
    # 1. Register agents for Sales, Personal, Engineering, Marketing
    agents = [
        ("sales_closer", "sales"),
        ("personal_assistant", "personal"),
        ("infra_engineer", "engineering"),
        ("marketing_specialist", "marketing"),
    ]
    for identity, dept in agents:
        contract = AgentContract(
            identity=identity,
            department=dept,
            goal=f"Onboard enterprise clients via {dept}",
            responsibilities=["customer_onboarding"],
            forbidden_actions=[],
            allowed_tools=["onboarding_tool"],
            memory_access="department_wide",
            output_schema={},
        )
        await full_os_kernel.send_event(
            create_test_event(
                source=harness_client.name,
                destination="agent_registry",
                event_type="registry.register_agent",
                payload={"contract": contract.model_dump()},
            )
        )
        await harness_client.wait_for_event(
            event_type="registry.agent_registered",
            predicate=lambda e, aid=identity: e.payload.get("identity") == aid,
            timeout=3.0,
        )

    # 2. Build Customer Onboarding DAG
    t1 = create_test_task(
        description="Sales closes $250k enterprise contract deal with client Globex Corp",
        requester=harness_client.name,
    )
    t2 = create_test_task(
        description="Personal assistant schedules onboarding kick-off meeting with Globex Corp executive team",
        requester=harness_client.name,
        dependencies=[t1.id],
    )
    t3 = create_test_task(
        description="Engineering provisions dedicated cloud tenant environment and API keys for Globex Corp",
        requester=harness_client.name,
        dependencies=[t2.id],
    )
    t4 = create_test_task(
        description="Marketing sends welcome kit, onboarding documentation, and admin portal access to Globex Corp",
        requester=harness_client.name,
        dependencies=[t3.id],
    )

    for task_obj in [t1, t2, t3, t4]:
        assert_valid_task(task_obj)

    onboarding_dag = create_test_dag(
        name="Globex Corp Customer Onboarding DAG",
        requester=harness_client.name,
        tasks=[t1, t2, t3, t4],
    )
    assert_valid_dag(onboarding_dag)

    await full_os_kernel.send_event(
        create_test_event(
            source=harness_client.name,
            destination="scheduler",
            event_type="dag.create",
            payload={"dag": onboarding_dag.model_dump()},
        )
    )

    # 3. Wait for all 4 tasks to complete in sequence
    completed_task_ids = []
    for task_obj in [t1, t2, t3, t4]:
        comp_evt = await harness_client.wait_for_event(
            event_type="task.complete",
            predicate=lambda e, tid=task_obj.id: e.payload.get("task_id") == tid,
            timeout=5.0,
        )
        completed_task_ids.append(comp_evt.payload["task_id"])
        assert_valid_cost_tracker_payload(comp_evt.payload)

    assert completed_task_ids == [t1.id, t2.id, t3.id, t4.id]

    dag_comp = await harness_client.wait_for_event(
        event_type="dag.complete",
        predicate=lambda e: e.payload.get("dag_id") == onboarding_dag.id,
        timeout=5.0,
    )
    assert dag_comp.payload["dag_id"] == onboarding_dag.id

    # 4. Store customer record in MemoryEngine
    cust_record = create_test_knowledge(
        observation="Account Globex Corp successfully onboarded with dedicated tenant environment.",
        source="sales_onboarding_team",
        category="customer_account",
        confidence=1.0,
        importance=8,
    )
    await full_os_kernel.send_event(
        create_test_event(
            source=harness_client.name,
            destination="memory_engine",
            event_type="memory.store_knowledge",
            payload={"knowledge": cust_record.model_dump()},
        )
    )
    await harness_client.wait_for_event(
        event_type="memory.knowledge_stored",
        predicate=lambda e: e.payload.get("knowledge_id") == cust_record.id,
        timeout=3.0,
    )

    # 5. Verify customer record retrieval
    await full_os_kernel.send_event(
        create_test_event(
            source=harness_client.name,
            destination="memory_engine",
            event_type="memory.query_knowledge",
            payload={"query": "Globex Corp"},
        )
    )
    query_results = await harness_client.wait_for_event(
        event_type="memory.query_results",
        predicate=lambda e: e.payload.get("query") == "Globex Corp",
        timeout=3.0,
    )
    assert len(query_results.payload["results"]) > 0
    assert "Globex Corp" in query_results.payload["results"][0]["observation"]
