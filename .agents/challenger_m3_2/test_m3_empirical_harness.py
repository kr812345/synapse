import pytest
import asyncio
from datetime import datetime, timezone
from shared.models import Event
from kernel.kernel import Kernel
from departments.marketing.manager import MarketingManager
from departments.marketing.social_worker import SocialWorker
from departments.marketing.content_worker import ContentWorker
from departments.sales.manager import SalesManager
from departments.sales.outreach_worker import OutreachWorker
from departments.personal.manager import PersonalManager
from departments.personal.assistant_worker import AssistantWorker
from departments.echo.echo_manager import EchoDepartment
from shared.interfaces import Module

class MockEventCollector(Module):
    """Collector module to capture events sent by Kernel during tests."""
    def __init__(self, name: str = "test_collector"):
        self._name = name
        self.received_events = []

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel):
        pass

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)


@pytest.mark.asyncio
async def test_forbidden_actions_direct_execution():
    """Test 1.1: Verify forbidden action policies raise explicit PermissionError on direct execution."""
    social = SocialWorker()
    mkt_mgr = MarketingManager()
    content = ContentWorker()
    sales_mgr = SalesManager()
    outreach = OutreachWorker()
    personal_mgr = PersonalManager()
    assistant = AssistantWorker()

    # 1. Marketing SocialWorker: post_without_approval
    with pytest.raises(PermissionError) as exc_info:
        await social.execute({"description": "Post launch update", "action": "post_without_approval"})
    assert "post_without_approval" in str(exc_info.value)

    # 2. Marketing Manager: spend_over_budget
    with pytest.raises(PermissionError) as exc_info:
        await mkt_mgr.execute({"description": "Huge campaign", "action": "spend_over_budget"})
    assert "spend_over_budget" in str(exc_info.value)

    # 3. Marketing ContentWorker: publish_unapproved_copy
    with pytest.raises(PermissionError) as exc_info:
        await content.execute({"description": "Blog post", "action": "publish_unapproved_copy"})
    assert "publish_unapproved_copy" in str(exc_info.value)

    # 4. Sales Manager: grant_unauthorized_discount
    with pytest.raises(PermissionError) as exc_info:
        await sales_mgr.execute({"description": "Big deal", "action": "grant_unauthorized_discount"})
    assert "grant_unauthorized_discount" in str(exc_info.value)

    # 5. Sales Manager: delete_leads
    with pytest.raises(PermissionError) as exc_info:
        await sales_mgr.execute({"description": "Clean database", "action": "delete_leads"})
    assert "delete_leads" in str(exc_info.value)

    # 6. Sales OutreachWorker: send_spam_blast
    with pytest.raises(PermissionError) as exc_info:
        await outreach.execute({"description": "Cold email", "action": "send_spam_blast"})
    assert "send_spam_blast" in str(exc_info.value)

    # 7. Personal Manager: authorize_payments
    with pytest.raises(PermissionError) as exc_info:
        await personal_mgr.execute({"description": "Pay invoice", "action": "authorize_payments"})
    assert "authorize_payments" in str(exc_info.value)

    # 8. Personal AssistantWorker: delete_emails
    with pytest.raises(PermissionError) as exc_info:
        await assistant.execute({"description": "Clean inbox", "action": "delete_emails"})
    assert "delete_emails" in str(exc_info.value)


@pytest.mark.asyncio
async def test_forbidden_actions_via_kernel_events():
    """Test 1.2: Verify forbidden actions rejected and emit department.task_failed via Kernel event routing."""
    kernel = Kernel()
    collector = MockEventCollector("test_collector")
    kernel.register_module(collector)

    mkt_mgr = MarketingManager()
    sales_mgr = SalesManager()
    personal_mgr = PersonalManager()

    kernel.register_module(mkt_mgr)
    kernel.register_module(sales_mgr)
    kernel.register_module(personal_mgr)

    # 1. Marketing spend_over_budget event
    evt_mkt = Event(
        source="test_collector",
        destination="department.marketing",
        event_type="department.execute_task",
        payload={"task": {"id": "task_mkt_1", "description": "Overspend task", "action": "spend_over_budget"}}
    )
    await kernel.send_event(evt_mkt)

    # 2. Sales grant_unauthorized_discount event
    evt_sales = Event(
        source="test_collector",
        destination="department.sales",
        event_type="department.execute_task",
        payload={"task": {"id": "task_sales_1", "description": "Discount task", "action": "grant_unauthorized_discount"}}
    )
    await kernel.send_event(evt_sales)

    # 3. Personal authorize_payments event
    evt_prs = Event(
        source="test_collector",
        destination="department.personal",
        event_type="department.execute_task",
        payload={"task": {"id": "task_prs_1", "description": "Payment task", "action": "authorize_payments"}}
    )
    await kernel.send_event(evt_prs)

    failed_events = [e for e in collector.received_events if e.event_type == "department.task_failed"]
    assert len(failed_events) == 3

    failed_tasks = {e.payload.get("task_id"): e.payload.get("error") for e in failed_events}
    assert "task_mkt_1" in failed_tasks
    assert "spend_over_budget" in failed_tasks["task_mkt_1"]
    assert "task_sales_1" in failed_tasks
    assert "grant_unauthorized_discount" in failed_tasks["task_sales_1"]
    assert "task_prs_1" in failed_tasks
    assert "authorize_payments" in failed_tasks["task_prs_1"]


@pytest.mark.asyncio
async def test_kernel_registration_and_health():
    """Test 2.1: Register all M3 department modules with Kernel and verify health status."""
    kernel = Kernel()
    mkt = MarketingManager()
    sales = SalesManager()
    prs = PersonalManager()
    echo = EchoDepartment()

    kernel.register_module(mkt)
    kernel.register_module(sales)
    kernel.register_module(prs)
    kernel.register_module(echo)

    registered = kernel.list_modules()
    assert "department.marketing" in registered
    assert "department.sales" in registered
    assert "department.personal" in registered
    assert "echo_department" in registered

    health = kernel.get_health_status()
    assert health["status"] == "healthy"
    assert health["module_count"] == 4


@pytest.mark.asyncio
async def test_unicast_event_routing_and_task_completed():
    """Test 2.2: Verify unicast event routing to all M3 departments and receipt of department.task_completed / pong."""
    kernel = Kernel()
    collector = MockEventCollector("test_collector")
    kernel.register_module(collector)

    kernel.register_module(MarketingManager())
    kernel.register_module(SalesManager())
    kernel.register_module(PersonalManager())
    kernel.register_module(EchoDepartment())

    # 1. Marketing unicast
    await kernel.send_event(Event(
        source="test_collector",
        destination="department.marketing",
        event_type="department.execute_task",
        payload={"task": {"id": "mkt_task_100", "description": "New social marketing campaign", "budget": 1000}}
    ))

    # 2. Sales unicast
    await kernel.send_event(Event(
        source="test_collector",
        destination="department.sales",
        event_type="department.execute_task",
        payload={"task": {"id": "sales_task_100", "description": "Outreach pitch for enterprise lead", "lead_score": 45, "company": "Acme"}}
    ))

    # 3. Personal unicast
    await kernel.send_event(Event(
        source="test_collector",
        destination="department.personal",
        event_type="department.execute_task",
        payload={"task": {"id": "prs_task_100", "description": "Schedule executive calendar sync"}}
    ))

    # 4. Echo ping unicast
    echo_payload = {"ping_id": 99, "nested": {"key": "value"}}
    await kernel.send_event(Event(
        source="test_collector",
        destination="echo_department",
        event_type="ping",
        payload=echo_payload
    ))

    completed = [e for e in collector.received_events if e.event_type == "department.task_completed"]
    pongs = [e for e in collector.received_events if e.event_type == "pong"]

    assert len(completed) == 3
    assert len(pongs) == 1

    completed_ids = {e.payload["task_id"] for e in completed}
    assert completed_ids == {"mkt_task_100", "sales_task_100", "prs_task_100"}
    assert pongs[0].payload["original_payload"] == echo_payload


@pytest.mark.asyncio
async def test_event_cascade_workflow():
    """Test 2.3: Verify multi-stage event cascade: Marketing -> Sales -> Personal -> Echo."""
    kernel = Kernel()
    collector = MockEventCollector("test_collector")
    kernel.register_module(collector)

    kernel.register_module(MarketingManager())
    kernel.register_module(SalesManager())
    kernel.register_module(PersonalManager())
    kernel.register_module(EchoDepartment())

    cascade_log = []

    class CascadeCoordinator(Module):
        @property
        def name(self) -> str:
            return "coordinator"

        def set_kernel(self, k):
            self.k = k

        async def handle_event(self, event: Event) -> None:
            if event.event_type == "department.task_completed":
                source = event.source
                task_id = event.payload.get("task_id")
                cascade_log.append((source, task_id))

                if source == "department.marketing":
                    # Cascade to Sales
                    await self.k.send_event(Event(
                        source="coordinator",
                        destination="department.sales",
                        event_type="department.execute_task",
                        payload={"task": {"id": "cascade_sales_2", "description": "Qualify marketing leads", "lead_score": 75, "company": "Global Corp"}}
                    ))
                elif source == "department.sales":
                    # Cascade to Personal
                    await self.k.send_event(Event(
                        source="coordinator",
                        destination="department.personal",
                        event_type="department.execute_task",
                        payload={"task": {"id": "cascade_prs_3", "description": "Schedule call with qualified lead"}}
                    ))
                elif source == "department.personal":
                    # Cascade to Echo ping
                    await self.k.send_event(Event(
                        source="coordinator",
                        destination="echo_department",
                        event_type="ping",
                        payload={"cascade_completed": True, "steps": 3}
                    ))
            elif event.event_type == "pong":
                cascade_log.append(("echo_department", "pong"))

    coord = CascadeCoordinator()
    kernel.register_module(coord)

    # Start cascade by triggering Marketing
    await kernel.send_event(Event(
        source="coordinator",
        destination="department.marketing",
        event_type="department.execute_task",
        payload={"task": {"id": "cascade_mkt_1", "description": "Launch product campaign"}}
    ))

    assert len(cascade_log) == 4
    assert cascade_log[0] == ("department.marketing", "cascade_mkt_1")
    assert cascade_log[1] == ("department.sales", "cascade_sales_2")
    assert cascade_log[2] == ("department.personal", "cascade_prs_3")
    assert cascade_log[3] == ("echo_department", "pong")


@pytest.mark.asyncio
async def test_edge_cases_and_error_handling():
    """Test 3: Stress-test edge cases in M3 departments."""
    mkt = MarketingManager()
    sales = SalesManager()
    prs = PersonalManager()
    assistant = AssistantWorker()

    # Edge case 1: Negative budget in marketing
    with pytest.raises(ValueError) as exc:
        await mkt.execute({"description": "Campaign", "budget": -500})
    assert "negative" in str(exc.value)

    # Edge case 2: Lead score thresholds in sales
    res_unqual = await sales.execute({"description": "Lead check", "lead_score": -10})
    assert res_unqual["qualification"] == "unqualified"

    res_disqual = await sales.execute({"description": "Lead check", "lead_score": 25})
    assert res_disqual["qualification"] == "disqualified"

    res_qual = await sales.execute({"description": "Lead check", "lead_score": 30})
    assert res_qual["qualification"] == "qualified"

    # Edge case 3: Missing CRM fields
    res_crm = await sales.execute({"description": "Lead check", "email": "", "contact_name": ""})
    assert "email" in res_crm["missing_crm_fields"]
    assert "contact_name" in res_crm["missing_crm_fields"]

    # Edge case 4: Extremely long content in social worker
    social = SocialWorker()
    long_content = "X" * 10000
    res_social = await social.execute({"description": "Post update", "content": long_content, "channel": "linkedin"})
    assert res_social["status"] == "success"
    assert len(res_social["post_content"]) > 10000

    # Edge case 5: Personal manager oversight vs assistant delegation
    res_fin = await prs.execute({"description": "Review quarterly finance expenses"})
    assert res_fin["oversight_type"] == "finance_and_contacts"
    assert res_fin["result"]["payments_authorized"] is False

    res_sched = await prs.execute({"description": "Schedule meeting with team"})
    assert res_sched["delegated_to"] == assistant.name
