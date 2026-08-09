import pytest
import asyncio
import sys
import logging
from typing import Dict, Any, List

sys.path.insert(0, "/root/synapse")

from shared.models import Event
from shared.interfaces import Module
from kernel.kernel import Kernel
from departments.marketing.manager import MarketingManager
from departments.marketing.social_worker import SocialWorker
from departments.marketing.content_worker import ContentWorker
from departments.sales.manager import SalesManager
from departments.sales.outreach_worker import OutreachWorker, SalesWorker
from departments.personal.manager import PersonalManager
from departments.personal.assistant_worker import AssistantWorker
from departments.echo.echo_manager import EchoDepartment

logging.basicConfig(level=logging.INFO)

class TestReceiver(Module):
    def __init__(self, name: str = "test_receiver"):
        self._name = name
        self.kernel = None
        self.received_events: List[Event] = []

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel) -> None:
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)

class CustomTaskObj:
    def __init__(self, description: str, budget: float = None, lead_score: int = 50, company: str = None, action: str = ""):
        self.description = description
        self.budget = budget
        self.lead_score = lead_score
        self.company = company
        self.action = action

def check_no_mock_strings(obj: Any, path: str = "") -> List[str]:
    """Recursively inspect object for 'mock' or 'stub' terms in keys and string values."""
    violations = []
    forbidden_terms = ["mocked", "stub", "fake_data"]
    
    if isinstance(obj, dict):
        for k, v in obj.items():
            for term in forbidden_terms:
                if term in str(k).lower():
                    violations.append(f"Forbidden term '{term}' in key '{path}.{k}'")
            violations.extend(check_no_mock_strings(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            violations.extend(check_no_mock_strings(item, f"{path}[{idx}]"))
    elif isinstance(obj, str):
        for term in forbidden_terms:
            if term in obj.lower():
                violations.append(f"Forbidden term '{term}' in string value at '{path}': {obj}")
    return violations

@pytest.mark.asyncio
async def test_marketing_edge_cases():
    mkt_mgr = MarketingManager()

    # 1. Negative budgets
    for neg_budget in [-1, -0.01, -999999]:
        try:
            await mkt_mgr.execute({"description": "Test negative budget", "budget": neg_budget})
            pytest.fail(f"MarketingManager failed to raise ValueError for budget {neg_budget}")
        except ValueError as e:
            assert "negative" in str(e).lower()

    # 2. Custom task object handling
    obj_task = CustomTaskObj(description="Object based marketing task", budget=2500)
    res_obj = await mkt_mgr.execute(obj_task)
    assert res_obj["status"] == "success"
    assert res_obj["budget"] == 2500

    # 3. String task handling
    res_str = await mkt_mgr.execute("Simple string marketing campaign task")
    assert res_str["status"] == "success"
    assert res_str["budget"] == 0

    # 4. SocialWorker long posts (>10,000 chars)
    soc_worker = SocialWorker()
    long_content = "A" * 15000
    res_long = await soc_worker.execute({"description": "Long post", "content": long_content, "channel": "twitter"})
    assert res_long["status"] == "success"
    assert len(res_long["post_content"]) >= 15000
    assert res_long["post_content"].startswith("[TWITTER]")

    # 5. Unsupported channels
    for ch in ["tiktok", "myspace", "custom_chan", "", "123"]:
        res_ch = await soc_worker.execute({"description": "Test channel", "content": "Hello", "channel": ch})
        assert res_ch["status"] == "success"
        assert res_ch["channel"] == ch
        assert f"[{str(ch).upper()}]" in res_ch["post_content"]

    # 6. ContentWorker execution
    cnt_worker = ContentWorker()
    res_cnt = await cnt_worker.execute({"description": "Write deep technical blog article"})
    assert res_cnt["status"] == "success"
    assert "content article generated" in res_cnt["result"]

@pytest.mark.asyncio
async def test_sales_edge_cases():
    sales_mgr = SalesManager()

    # 1. Lead score limits: <=0 (unqualified), <30 (disqualified), >=30 (qualified)
    test_scores = [
        (-50, "unqualified"),
        (0, "unqualified"),
        (1, "disqualified"),
        (29, "disqualified"),
        (29.9, "disqualified"),
        (30, "qualified"),
        (30.0, "qualified"),
        (100, "qualified")
    ]
    for score, expected_qual in test_scores:
        res = await sales_mgr.execute({"description": "Qualify lead", "lead_score": score})
        assert res["status"] == "success"
        assert res["qualification"] == expected_qual, f"Score {score} expected {expected_qual}, got {res['qualification']}"

    # 2. Empty company defaults to 'unknown'
    for empty_co in ["", None, False]:
        res_co = await sales_mgr.execute({"description": "Sales lead", "company": empty_co})
        assert res_co["company"] == "unknown"

    # 3. Missing CRM fields
    res_crm = await sales_mgr.execute({
        "description": "Lead process",
        "email": "",
        "contact_name": None,
        "phone": ""
    })
    assert "email" in res_crm["missing_crm_fields"]
    assert "contact_name" in res_crm["missing_crm_fields"]

    # 4. Custom Task Object
    obj_task = CustomTaskObj(description="Sales lead pitch task", lead_score=45, company="Enterprise Co")
    res_obj = await sales_mgr.execute(obj_task)
    assert res_obj["status"] == "success"
    assert res_obj["qualification"] == "qualified"
    assert res_obj["company"] == "Enterprise Co"

    # 5. OutreachWorker pitch generation
    outreach = OutreachWorker()
    res_pitch = await outreach.execute({"description": "Outreach pitch for enterprise SaaS"})
    assert res_pitch["status"] == "success"
    assert "custom sales pitch generated" in res_pitch["result"]

@pytest.mark.asyncio
async def test_personal_edge_cases():
    prs_mgr = PersonalManager()
    asst = AssistantWorker()

    # 1. Calendar/Schedule tasks -> AssistantWorker delegation
    for sched_keyword in ["Schedule executive sync", "Calendar invite update", "Meeting room booking", "Weekly Agenda review"]:
        res = await prs_mgr.execute({"description": sched_keyword})
        assert res["status"] == "success"
        assert res["delegated_to"] == "Charlie Assistant"
        assert res["result"]["action"] == "calendar_management"

    # 2. Email tasks -> AssistantWorker delegation
    res_email = await prs_mgr.execute({"description": "Draft response to email from client"})
    assert res_email["status"] == "success"
    assert res_email["delegated_to"] == "Charlie Assistant"
    assert res_email["result"]["action"] == "email_processing"

    # 3. Custom task object
    obj_task = CustomTaskObj(description="Schedule doctor appointment")
    res_obj = await prs_mgr.execute(obj_task)
    assert res_obj["status"] == "success"
    assert res_obj["delegated_to"] == "Charlie Assistant"

    # 4. Forbidden action on AssistantWorker
    try:
        await asst.execute({"description": "Clean inbox", "action": "delete_emails"})
        pytest.fail("AssistantWorker failed to raise PermissionError on delete_emails")
    except PermissionError as e:
        assert "delete_emails" in str(e)

    # 5. PersonalManager Finance/Contacts oversight
    res_fin = await prs_mgr.execute({"description": "Review monthly expenses and personal contacts"})
    assert res_fin["status"] == "success"
    assert res_fin["oversight_type"] == "finance_and_contacts"
    assert res_fin["result"]["payments_authorized"] is False

    # 6. PersonalManager forbidden action authorize_payments
    try:
        await prs_mgr.execute({"description": "Pay invoice", "action": "authorize_payments"})
        pytest.fail("PersonalManager failed to raise PermissionError on authorize_payments")
    except PermissionError as e:
        assert "authorize_payments" in str(e)

@pytest.mark.asyncio
async def test_echo_edge_cases():
    kernel = Kernel()
    echo_dept = EchoDepartment()
    receiver = TestReceiver("echo_tester")

    kernel.register_module(echo_dept)
    kernel.register_module(receiver)

    # Deeply nested complex payload
    complex_payload = {
        "metadata": {
            "version": 2.0,
            "flags": [True, False, None],
            "nested_dict": {"level1": {"level2": {"level3": [1, 2, 3, "deep_string"]}}}
        },
        "records": [
            {"id": i, "val": f"item_{i}"} for i in range(100)
        ]
    }

    ping_event = Event(
        source=receiver.name,
        destination="echo_department",
        event_type="ping",
        payload=complex_payload
    )

    await kernel.send_event(ping_event)
    await asyncio.sleep(0.05)

    assert len(receiver.received_events) == 1
    pong_event = receiver.received_events[0]
    assert pong_event.event_type == "pong"
    assert pong_event.source == "echo_department"
    assert pong_event.destination == receiver.name
    assert pong_event.payload["original_payload"] == complex_payload

@pytest.mark.asyncio
async def test_all_outputs_no_mock_strings():
    mkt = MarketingManager()
    sls = SalesManager()
    prs = PersonalManager()
    soc = SocialWorker()
    cnt = ContentWorker()
    out = OutreachWorker()
    ast = AssistantWorker()

    tasks_to_test = [
        (mkt, {"description": "Marketing campaign", "budget": 1000, "specs": {"target": "B2B"}}),
        (sls, {"description": "Sales lead campaign", "lead_score": 50, "company": "Acme"}),
        (prs, {"description": "Schedule personal lunch"}),
        (prs, {"description": "Personal finance review"}),
        (soc, {"description": "Social post", "content": "Hello world"}),
        (cnt, {"description": "Write blog article"}),
        (out, {"description": "Sales pitch"}),
        (ast, {"description": "Email draft"})
    ]

    all_violations = []
    for agent, task in tasks_to_test:
        res = await agent.execute(task)
        violations = check_no_mock_strings(res, path=agent.name)
        all_violations.extend(violations)

    assert len(all_violations) == 0, f"Found mock string violations in output dicts: {all_violations}"

@pytest.mark.asyncio
async def test_concurrent_kernel_multi_department_cascade():
    kernel = Kernel()
    mkt = MarketingManager(id="mkt_mgr", name="Marketing Manager")
    sls = SalesManager(id="sls_mgr", name="Sales Manager")
    prs = PersonalManager(id="prs_mgr", name="Personal Manager")
    echo = EchoDepartment()
    receiver = TestReceiver("cascade_receiver")

    kernel.register_module(mkt)
    kernel.register_module(sls)
    kernel.register_module(prs)
    kernel.register_module(echo)
    kernel.register_module(receiver)

    events = [
        Event(source=receiver.name, destination="department.marketing", event_type="department.execute_task", payload={"task": {"id": "m1", "description": "Marketing campaign"}}),
        Event(source=receiver.name, destination="department.sales", event_type="department.execute_task", payload={"task": {"id": "s1", "description": "Sales lead", "lead_score": 75}}),
        Event(source=receiver.name, destination="department.personal", event_type="department.execute_task", payload={"task": {"id": "p1", "description": "Schedule meeting"}}),
        Event(source=receiver.name, destination="echo_department", event_type="ping", payload={"msg": "ping1"}),
    ]

    for evt in events:
        await kernel.send_event(evt)

    await asyncio.sleep(0.1)

    assert len(receiver.received_events) == 4
    event_types = [e.event_type for e in receiver.received_events]
    assert event_types.count("department.task_completed") == 3
    assert event_types.count("pong") == 1
