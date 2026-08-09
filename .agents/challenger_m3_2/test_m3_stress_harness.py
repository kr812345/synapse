import pytest
import asyncio
import subprocess
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

class EventTracker(Module):
    def __init__(self, name: str = "tracker"):
        self._name = name
        self.events = []

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel):
        pass

    async def handle_event(self, event: Event) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_no_mock_strings_in_departments():
    """Verify zero mock strings exist across department implementations."""
    cmd = "grep -rn -i 'mocked' departments/marketing departments/sales departments/personal departments/echo"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert res.returncode != 0 or not res.stdout.strip(), f"Found mock strings in departments: {res.stdout}"


@pytest.mark.asyncio
async def test_concurrent_kernel_events_m3():
    """Stress-test Kernel with 50 concurrent events across all M3 department modules."""
    kernel = Kernel()
    tracker = EventTracker("tracker")
    kernel.register_module(tracker)

    kernel.register_module(MarketingManager())
    kernel.register_module(SalesManager())
    kernel.register_module(PersonalManager())
    kernel.register_module(EchoDepartment())

    events = []
    for i in range(50):
        if i % 4 == 0:
            target = "department.marketing"
            task_id = f"mkt_conc_{i}"
            payload = {"task": {"id": task_id, "description": f"Campaign task {i}", "budget": 100 * (i + 1)}}
        elif i % 4 == 1:
            target = "department.sales"
            task_id = f"sales_conc_{i}"
            payload = {"task": {"id": task_id, "description": f"Lead task {i}", "lead_score": i * 2, "company": f"Company_{i}"}}
        elif i % 4 == 2:
            target = "department.personal"
            task_id = f"prs_conc_{i}"
            payload = {"task": {"id": task_id, "description": f"Personal schedule task {i}"}}
        else:
            target = "echo_department"
            task_id = f"echo_conc_{i}"
            payload = {"seq": i, "data": f"ping_{i}"}

        event_type = "ping" if target == "echo_department" else "department.execute_task"
        events.append(Event(
            source="tracker",
            destination=target,
            event_type=event_type,
            payload=payload
        ))

    await asyncio.gather(*[kernel.send_event(e) for e in events])

    completed_events = [e for e in tracker.events if e.event_type in ("department.task_completed", "pong")]
    assert len(completed_events) == 50


@pytest.mark.asyncio
async def test_broadcast_event_handling():
    """Verify system.shutdown broadcast event handling across M3 departments."""
    kernel = Kernel()
    tracker = EventTracker("tracker")
    kernel.register_module(tracker)

    mkt = MarketingManager()
    sales = SalesManager()
    prs = PersonalManager()
    echo = EchoDepartment()

    kernel.register_module(mkt)
    kernel.register_module(sales)
    kernel.register_module(prs)
    kernel.register_module(echo)

    # Broadcast event
    bcast = Event(
        source="tracker",
        destination="*",
        event_type="system.shutdown",
        payload={"reason": "test shutdown"}
    )
    # Sending broadcast should not crash any department modules
    await kernel.send_event(bcast)
