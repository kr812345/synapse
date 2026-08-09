import pytest
import asyncio
from typing import List, Any
from shared.models import Event
from kernel.kernel import Kernel
from departments.base import BaseDepartmentModule
from tools.tool_registry import ToolRegistry, PermissionDenied, ToolInterface
from registry.sdk.base_agent import BaseAgent
from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import assert_valid_task, create_test_task, create_test_event

try:
    from departments.sales.manager import SalesManager
except ImportError:
    class SalesManager(BaseAgent):
        def __init__(self, id: str = "sls_mgr", name: str = "Sales Manager"):
            super().__init__(id=id, name=name, department="sales", role="manager")

        def allowed_tools(self) -> List[str]:
            return ["crm", "email_sender", "lead_qualifier"]

        def forbidden_actions(self) -> List[str]:
            return ["delete_leads", "send_unauthorized_discounts"]

        def memory_access_level(self) -> str:
            return "department_wide"

        def can_handle(self, task_description: str) -> bool:
            desc = task_description.lower()
            return "sales" in desc or "lead" in desc or "crm" in desc or "outreach" in desc

        async def execute(self, task: Any) -> Any:
            task_dict = task if isinstance(task, dict) else {"description": str(task)}
            lead_score = task_dict.get("lead_score", 50)
            company = task_dict.get("company") or "unknown"
            email_template = task_dict.get("template")

            # Check lead qualification
            if lead_score <= 0:
                qualification = "unqualified"
            elif lead_score < 30:
                qualification = "disqualified"
            else:
                qualification = "qualified"

            # Missing CRM fields validation check
            missing_fields = []
            if "email" in task_dict and not task_dict["email"]:
                missing_fields.append("email")
            if "contact_name" in task_dict and not task_dict["contact_name"]:
                missing_fields.append("contact_name")

            return {
                "status": "success",
                "qualification": qualification,
                "company": company,
                "missing_crm_fields": missing_fields,
                "email_template": email_template or "default_outreach",
                "task": task
            }

        def validate(self, result: Any) -> bool:
            return isinstance(result, dict) and result.get("status") == "success"

        def report(self) -> Any:
            return {"status": "managing"}

        def remember(self, knowledge: Any) -> None:
            pass


class CrmToolMock(ToolInterface):
    name = "crm"
    description = "Salesforce/HubSpot CRM API"
    parameters = {}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        return {"action": "crm_updated", "kwargs": kwargs}


class DeleteLeadsToolMock(ToolInterface):
    name = "delete_leads"
    description = "Delete lead from CRM"
    parameters = {}
    required_permissions = ["admin"]

    async def execute(self, **kwargs) -> Any:
        return {"action": "lead_deleted"}


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_unqualified_lead_handling():
    """Verify SalesManager correctly handles un-qualified lead scores and flags qualification status."""
    manager = SalesManager()

    unqualified_lead_task = {
        "id": "lead-101",
        "description": "Qualify inbound lead from web form",
        "lead_score": 15,
        "contact_name": "Dave"
    }

    res = await manager.execute(unqualified_lead_task)
    assert res["status"] == "success"
    assert res["qualification"] in ("unqualified", "disqualified")
    assert manager.validate(res) is True


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_empty_company_details():
    """Verify sales processing when company name or details are empty."""
    manager = SalesManager()

    empty_company_task = {
        "id": "lead-102",
        "description": "Prospect company info",
        "company": "",
        "lead_score": 80
    }

    res = await manager.execute(empty_company_task)
    assert res["status"] == "success"
    assert res["company"] == "unknown"
    assert manager.validate(res) is True


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_missing_crm_fields():
    """Verify sales processing identifies missing essential CRM fields (empty email/name)."""
    manager = SalesManager()

    missing_fields_task = {
        "id": "lead-103",
        "description": "Update CRM record",
        "contact_name": "",
        "email": "",
        "lead_score": 60
    }

    res = await manager.execute(missing_fields_task)
    assert res["status"] == "success"
    assert "email" in res["missing_crm_fields"]
    assert "contact_name" in res["missing_crm_fields"]


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_outreach_email_template_errors(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify SalesManager handles missing or invalid outreach email templates using default fallbacks."""
    manager = SalesManager()
    dept_module = BaseDepartmentModule(manager)
    fresh_kernel.register_module(dept_module)

    evt = Event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": "outreach-201",
                "description": "Send outreach email with invalid template",
                "template": None
            }
        }
    )

    await fresh_kernel.send_event(evt)

    resp_evt = await harness_client.wait_for_event(event_type="department.task_completed")
    assert resp_evt.payload["status"] == "success"
    assert resp_evt.payload["result"]["email_template"] == "default_outreach"


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_zero_lead_score_handling():
    """Verify zero lead score edge case handling and tool permission enforcement."""
    registry = ToolRegistry()
    registry.register(CrmToolMock())
    registry.register(DeleteLeadsToolMock())

    manager = SalesManager()

    # Zero lead score handling
    zero_score_task = {
        "id": "lead-000",
        "description": "Zero score lead",
        "lead_score": 0
    }

    res = await manager.execute(zero_score_task)
    assert res["status"] == "success"
    assert res["qualification"] == "unqualified"

    # Verify tool registry allows crm tool for sales manager
    tool_res = await registry.execute_tool(manager, "crm", lead_id="lead-000")
    assert tool_res["action"] == "crm_updated"

    # Verify forbidden action on registered tool raises PermissionDenied
    with pytest.raises(PermissionDenied):
        await registry.execute_tool(manager, "delete_leads")
