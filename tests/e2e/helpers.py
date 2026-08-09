"""
Helper utilities and schema validation assertion functions for Synapse AI OS E2E testing.
Covers Event, Task, DAG, Knowledge, and CostTracker payload structures.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from shared.models import Event, Task, DAG, Knowledge

VALID_TASK_STATUSES = {
    "pending",
    "agent_assigned",
    "scheduling",
    "executing",
    "validating",
    "completed",
    "failed",
}

VALID_DAG_STATUSES = {
    "pending",
    "executing",
    "completed",
    "failed",
}

def assert_valid_event(event: Event) -> None:
    """Assert that an object is a structurally valid Event model."""
    assert isinstance(event, Event), f"Expected Event instance, got {type(event)}"
    assert isinstance(event.id, str) and len(event.id) > 0, "Event.id must be a non-empty string"
    assert isinstance(event.source, str) and len(event.source) > 0, "Event.source must be a non-empty string"
    assert isinstance(event.destination, str) and len(event.destination) > 0, "Event.destination must be a non-empty string"
    assert isinstance(event.event_type, str) and len(event.event_type) > 0, "Event.event_type must be a non-empty string"
    assert isinstance(event.payload, dict), f"Event.payload must be a dict, got {type(event.payload)}"
    assert isinstance(event.timestamp, datetime), f"Event.timestamp must be a datetime, got {type(event.timestamp)}"

def assert_event_matches(
    event: Event,
    source: Optional[str] = None,
    destination: Optional[str] = None,
    event_type: Optional[str] = None,
    payload_subset: Optional[Dict[str, Any]] = None
) -> None:
    """Assert that an event matches expected header attributes and optional payload subset."""
    assert_valid_event(event)
    if source is not None:
        assert event.source == source, f"Expected event.source '{source}', got '{event.source}'"
    if destination is not None:
        assert event.destination == destination, f"Expected event.destination '{destination}', got '{event.destination}'"
    if event_type is not None:
        assert event.event_type == event_type, f"Expected event.event_type '{event_type}', got '{event.event_type}'"
    if payload_subset is not None:
        for k, v in payload_subset.items():
            assert k in event.payload, f"Expected key '{k}' in event payload, available keys: {list(event.payload.keys())}"
            assert event.payload[k] == v, f"Expected payload['{k}'] == '{v}', got '{event.payload[k]}'"

def assert_valid_task(task: Union[Task, Dict[str, Any]]) -> None:
    """Assert that an object or dictionary is a valid Task representation."""
    if isinstance(task, Task):
        assert isinstance(task.id, str) and len(task.id) > 0, "Task.id must be non-empty"
        assert isinstance(task.description, str) and len(task.description) > 0, "Task.description must be non-empty"
        assert isinstance(task.requester, str) and len(task.requester) > 0, "Task.requester must be non-empty"
        assert task.status in VALID_TASK_STATUSES, f"Task.status '{task.status}' not in {VALID_TASK_STATUSES}"
        assert isinstance(task.created_at, datetime), "Task.created_at must be datetime"
        if task.assigned_agent is not None:
            assert isinstance(task.assigned_agent, str), "Task.assigned_agent must be str if present"
        if task.result is not None:
            assert isinstance(task.result, dict), "Task.result must be dict if present"
        if task.dependencies is not None:
            assert isinstance(task.dependencies, list), "Task.dependencies must be list"
    elif isinstance(task, dict):
        assert "id" in task and isinstance(task["id"], str), "Task dict missing string 'id'"
        assert "description" in task and isinstance(task["description"], str), "Task dict missing string 'description'"
        assert "requester" in task and isinstance(task["requester"], str), "Task dict missing string 'requester'"
        assert "status" in task and task["status"] in VALID_TASK_STATUSES, f"Task dict status invalid: {task.get('status')}"
    else:
        raise AssertionError(f"Expected Task instance or dict, got {type(task)}")

def assert_valid_dag(dag: Union[DAG, Dict[str, Any]]) -> None:
    """Assert that an object or dictionary is a valid DAG representation."""
    if isinstance(dag, DAG):
        assert isinstance(dag.id, str) and len(dag.id) > 0, "DAG.id must be non-empty"
        assert isinstance(dag.name, str) and len(dag.name) > 0, "DAG.name must be non-empty"
        assert isinstance(dag.requester, str) and len(dag.requester) > 0, "DAG.requester must be non-empty"
        assert dag.status in VALID_DAG_STATUSES, f"DAG.status '{dag.status}' not in {VALID_DAG_STATUSES}"
        assert isinstance(dag.tasks, list), "DAG.tasks must be a list"
        for t in dag.tasks:
            assert_valid_task(t)
    elif isinstance(dag, dict):
        assert "id" in dag and isinstance(dag["id"], str), "DAG dict missing string 'id'"
        assert "name" in dag and isinstance(dag["name"], str), "DAG dict missing string 'name'"
        assert "requester" in dag and isinstance(dag["requester"], str), "DAG dict missing string 'requester'"
        assert "status" in dag and dag["status"] in VALID_DAG_STATUSES, f"DAG dict status invalid: {dag.get('status')}"
        if "tasks" in dag and isinstance(dag["tasks"], list):
            for t in dag["tasks"]:
                assert_valid_task(t)
    else:
        raise AssertionError(f"Expected DAG instance or dict, got {type(dag)}")

def assert_valid_knowledge(knowledge: Union[Knowledge, Dict[str, Any]]) -> None:
    """Assert that an object or dictionary is a valid Knowledge model."""
    if isinstance(knowledge, Knowledge):
        assert isinstance(knowledge.id, str) and len(knowledge.id) > 0, "Knowledge.id must be non-empty"
        assert isinstance(knowledge.observation, str) and len(knowledge.observation) > 0, "Knowledge.observation must be non-empty"
        assert isinstance(knowledge.source, str) and len(knowledge.source) > 0, "Knowledge.source must be non-empty"
        assert isinstance(knowledge.confidence, (float, int)) and 0.0 <= knowledge.confidence <= 1.0, f"Knowledge.confidence out of bounds: {knowledge.confidence}"
        assert isinstance(knowledge.category, str), "Knowledge.category must be str"
        assert isinstance(knowledge.importance, int), "Knowledge.importance must be int"
    elif isinstance(knowledge, dict):
        assert "id" in knowledge and isinstance(knowledge["id"], str), "Knowledge dict missing 'id'"
        assert "observation" in knowledge and isinstance(knowledge["observation"], str), "Knowledge dict missing 'observation'"
        assert "source" in knowledge and isinstance(knowledge["source"], str), "Knowledge dict missing 'source'"
        assert "confidence" in knowledge and isinstance(knowledge["confidence"], (float, int)), "Knowledge dict missing numeric 'confidence'"
    else:
        raise AssertionError(f"Expected Knowledge instance or dict, got {type(knowledge)}")

def assert_valid_cost_tracker_payload(payload: Dict[str, Any]) -> None:
    """
    Assert schema for CostTracker / Model Execution Result payloads.
    Must contain status/executed_by, token breakdown, and cost.
    """
    assert isinstance(payload, dict), f"CostTracker payload must be a dict, got {type(payload)}"
    
    # Check for result wrapper if present
    res = payload.get("result", payload)
    
    # Status or execution status
    assert "status" in res or "executed_by" in res, f"CostTracker payload missing 'status' or 'executed_by': {res}"
    
    # If cost is provided directly or inside result
    if "cost" in res:
        assert isinstance(res["cost"], (float, int)), f"Cost must be numeric, got {type(res['cost'])}"
        assert res["cost"] >= 0.0, f"Cost cannot be negative, got {res['cost']}"
        
    # If tokens dict is provided
    if "tokens" in res and isinstance(res["tokens"], dict):
        tokens = res["tokens"]
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            if key in tokens:
                assert isinstance(tokens[key], int), f"Token count '{key}' must be int, got {type(tokens[key])}"
                assert tokens[key] >= 0, f"Token count '{key}' cannot be negative"

def create_test_event(
    source: str = "test_harness",
    destination: str = "*",
    event_type: str = "test.event",
    payload: Optional[Dict[str, Any]] = None
) -> Event:
    """Factory function for building test Event instances."""
    return Event(
        source=source,
        destination=destination,
        event_type=event_type,
        payload=payload if payload is not None else {}
    )

def create_test_task(
    description: str = "Execute test task",
    requester: str = "test_requester",
    dependencies: Optional[List[str]] = None
) -> Task:
    """Factory function for building test Task instances."""
    return Task(
        description=description,
        requester=requester,
        dependencies=dependencies if dependencies is not None else []
    )

def create_test_dag(
    name: str = "Test Workflow DAG",
    requester: str = "test_requester",
    tasks: Optional[List[Task]] = None
) -> DAG:
    """Factory function for building test DAG instances."""
    if tasks is None:
        t1 = create_test_task("Task 1", requester=requester)
        tasks = [t1]
    return DAG(name=name, requester=requester, tasks=tasks)

def create_test_knowledge(
    observation: str = "System component baseline operational",
    source: str = "system_test",
    category: str = "test",
    confidence: float = 1.0,
    importance: int = 5
) -> Knowledge:
    """Factory function for building test Knowledge instances."""
    return Knowledge(
        observation=observation,
        source=source,
        category=category,
        confidence=confidence,
        importance=importance
    )
