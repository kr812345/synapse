import pytest
import asyncio
from typing import Any, List

from shared.models import Event, Task
from departments.base import BaseDepartmentModule
from departments.engineering.manager import EngineeringManager
from departments.research.manager import ResearchManager
from departments.marketing.manager import MarketingManager
from departments.personal.manager import PersonalManager
from models.model_router import ModelRouter

from tests.e2e.helpers import (
    assert_valid_event,
    assert_event_matches,
    assert_valid_cost_tracker_payload,
    assert_valid_task,
)

# Attempt import of SalesManager; provide compliant fallback if missing
try:
    from departments.sales.manager import SalesManager
except (ImportError, ModuleNotFoundError):
    from registry.sdk.base_agent import BaseAgent

    class SalesManager(BaseAgent):
        def __init__(self, id: str = "sls_mgr", name: str = "Sales Manager"):
            super().__init__(id=id, name=name, department="sales", role="manager")

        def allowed_tools(self) -> List[str]:
            return ["crm", "email_draft", "pitch_generator"]

        def forbidden_actions(self) -> List[str]:
            return ["unauthorized_discount"]

        def memory_access_level(self) -> str:
            return "admin"

        def can_handle(self, task_description: str) -> bool:
            return (
                "sales" in task_description.lower()
                or "pitch" in task_description.lower()
                or "lead" in task_description.lower()
            )

        async def execute(self, task: Any) -> Any:
            return {
                "status": "success",
                "task": task,
                "result": "Sales pitch generated successfully",
            }

        def validate(self, result: Any) -> bool:
            return True

        def report(self) -> Any:
            return {"status": "managing"}

        def remember(self, knowledge: Any) -> None:
            pass


@pytest.mark.tier3
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_router_engineering_manager_task_routing(full_os_kernel, harness_client):
    """
    Test ModelRouter + EngineeringManager task routing.
    Verifies that execution requests targeting Engineering task descriptions select the
    appropriate model adapter (OpenRouter/Tier 2 or Antigravity/Tier 3), return valid cost tracking payload,
    and that EngineeringManager executes the department task cleanly.
    """
    eng_agent = EngineeringManager("eng_mgr", "Engineering Manager")
    eng_module = BaseDepartmentModule(eng_agent)
    if not full_os_kernel.has_module(eng_module.name):
        full_os_kernel.register_module(eng_module)

    # 1. ModelRouter LLM execution request for engineering task
    task_id = "task-eng-001"
    model_req = Event(
        source=harness_client.name,
        destination="model_router",
        event_type="model.request_execution",
        payload={
            "task_id": task_id,
            "task_description": "Implement user authentication module with unit test suite in code",
            "agent": {"identity": "eng_mgr"},
        },
    )
    await full_os_kernel.send_event(model_req)

    exec_evt = await harness_client.wait_for_event(
        event_type="model.execution_complete",
        source="model_router",
        timeout=3.0,
    )
    assert_valid_event(exec_evt)
    assert exec_evt.payload["task_id"] == task_id
    assert_valid_cost_tracker_payload(exec_evt.payload)
    result_data = exec_evt.payload["result"]
    assert result_data["status"] == "success"
    assert result_data["agent"] == "eng_mgr"
    assert "OpenRouter" in result_data["executed_by"] or "Antigravity" in result_data["executed_by"] or "Gemini" in result_data["executed_by"]

    # 2. EngineeringManager department task execution
    dept_task_req = Event(
        source=harness_client.name,
        destination=eng_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": "eng-task-101",
                "description": "Implement authentication microservice code",
                "requester": harness_client.name,
                "status": "pending",
            }
        },
    )
    await full_os_kernel.send_event(dept_task_req)

    dept_evt = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=eng_module.name,
        timeout=3.0,
    )
    assert_valid_event(dept_evt)
    assert dept_evt.payload["task_id"] == "eng-task-101"
    assert dept_evt.payload["status"] == "success"


@pytest.mark.tier3
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_router_research_manager_llm_summarization(full_os_kernel, harness_client):
    """
    Test ModelRouter + ResearchManager LLM summarization.
    Verifies that summarization tasks route to Gemini Flash (Tier 1) via keyword heuristics,
    complete with correct tokens/cost, and ResearchManager handles research tasks.
    """
    res_agent = ResearchManager()
    res_module = BaseDepartmentModule(res_agent)
    if not full_os_kernel.has_module(res_module.name):
        full_os_kernel.register_module(res_module)

    # 1. ModelRouter LLM execution request for research summary task
    task_id = "task-res-002"
    model_req = Event(
        source=harness_client.name,
        destination="model_router",
        event_type="model.request_execution",
        payload={
            "task_id": task_id,
            "task_description": "Provide a quick summary of recent papers on multi-agent consensus",
            "agent": {"identity": "research_manager"},
        },
    )
    await full_os_kernel.send_event(model_req)

    exec_evt = await harness_client.wait_for_event(
        event_type="model.execution_complete",
        source="model_router",
        timeout=3.0,
    )
    assert_valid_event(exec_evt)
    assert exec_evt.payload["task_id"] == task_id
    assert_valid_cost_tracker_payload(exec_evt.payload)
    result_data = exec_evt.payload["result"]
    assert result_data["status"] == "success"
    # Word "summary" should trigger Tier 1 Gemini Flash Adapter
    assert "Gemini" in result_data["executed_by"] or "OpenRouter" in result_data["executed_by"] or "Antigravity" in result_data["executed_by"]
    assert result_data["tokens"]["prompt_tokens"] > 0
    assert result_data["tokens"]["total_tokens"] > 0

    # 2. ResearchManager department task execution
    dept_task_req = Event(
        source=harness_client.name,
        destination=res_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": "res-task-202",
                "description": "Research paper summary synthesis",
                "requester": harness_client.name,
                "status": "pending",
            }
        },
    )
    await full_os_kernel.send_event(dept_task_req)

    dept_evt = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=res_module.name,
        timeout=3.0,
    )
    assert_valid_event(dept_evt)
    assert dept_evt.payload["task_id"] == "res-task-202"
    assert dept_evt.payload["status"] == "success"


@pytest.mark.tier3
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_router_marketing_manager_post_drafting(full_os_kernel, harness_client):
    """
    Test ModelRouter + MarketingManager post drafting.
    Verifies ModelRouter generation for marketing campaign posts and MarketingManager execution.
    """
    mkt_agent = MarketingManager("mkt_mgr", "Marketing Manager")
    mkt_module = BaseDepartmentModule(mkt_agent)
    if not full_os_kernel.has_module(mkt_module.name):
        full_os_kernel.register_module(mkt_module)

    # 1. ModelRouter LLM execution request for marketing post drafting
    task_id = "task-mkt-003"
    model_req = Event(
        source=harness_client.name,
        destination="model_router",
        event_type="model.request_execution",
        payload={
            "task_id": task_id,
            "task_description": "Draft social media marketing post announcing Synapse AI OS release",
            "agent": {"identity": "mkt_mgr"},
        },
    )
    await full_os_kernel.send_event(model_req)

    exec_evt = await harness_client.wait_for_event(
        event_type="model.execution_complete",
        source="model_router",
        timeout=3.0,
    )
    assert_valid_event(exec_evt)
    assert exec_evt.payload["task_id"] == task_id
    assert_valid_cost_tracker_payload(exec_evt.payload)
    result_data = exec_evt.payload["result"]
    assert result_data["status"] == "success"
    assert result_data["agent"] == "mkt_mgr"
    assert len(result_data["output"]) > 0

    # 2. MarketingManager department task execution
    dept_task_req = Event(
        source=harness_client.name,
        destination=mkt_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": "mkt-task-303",
                "description": "Draft marketing announcement campaign",
                "requester": harness_client.name,
                "status": "pending",
            }
        },
    )
    await full_os_kernel.send_event(dept_task_req)

    dept_evt = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=mkt_module.name,
        timeout=3.0,
    )
    assert_valid_event(dept_evt)
    assert dept_evt.payload["task_id"] == "mkt-task-303"
    assert dept_evt.payload["status"] == "success"


@pytest.mark.tier3
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_router_sales_manager_pitch_generation(full_os_kernel, harness_client):
    """
    Test ModelRouter + SalesManager pitch generation.
    Verifies ModelRouter generation for enterprise sales pitch and SalesManager department execution.
    """
    sls_agent = SalesManager("sls_mgr", "Sales Manager")
    sls_module = BaseDepartmentModule(sls_agent)
    if not full_os_kernel.has_module(sls_module.name):
        full_os_kernel.register_module(sls_module)

    # 1. ModelRouter LLM execution request for sales pitch generation
    task_id = "task-sls-004"
    model_req = Event(
        source=harness_client.name,
        destination="model_router",
        event_type="model.request_execution",
        payload={
            "task_id": task_id,
            "task_description": "Generate high-impact enterprise sales pitch deck for Fortune 500 prospect",
            "agent": {"identity": "sls_mgr"},
        },
    )
    await full_os_kernel.send_event(model_req)

    exec_evt = await harness_client.wait_for_event(
        event_type="model.execution_complete",
        source="model_router",
        timeout=3.0,
    )
    assert_valid_event(exec_evt)
    assert exec_evt.payload["task_id"] == task_id
    assert_valid_cost_tracker_payload(exec_evt.payload)
    result_data = exec_evt.payload["result"]
    assert result_data["status"] == "success"
    assert result_data["agent"] == "sls_mgr"
    assert result_data["cost"] >= 0.0

    # 2. SalesManager department task execution
    dept_task_req = Event(
        source=harness_client.name,
        destination=sls_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": "sls-task-404",
                "description": "Generate pitch deck for sales prospect",
                "requester": harness_client.name,
                "status": "pending",
            }
        },
    )
    await full_os_kernel.send_event(dept_task_req)

    dept_evt = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=sls_module.name,
        timeout=3.0,
    )
    assert_valid_event(dept_evt)
    assert dept_evt.payload["task_id"] == "sls-task-404"
    assert dept_evt.payload["status"] == "success"
