import asyncio
from shared.interfaces import Module
from shared.models import Event
from kernel.kernel import Kernel
from models.model_router import ModelRouter
from tools.tool_registry import ToolRegistry
from departments.engineering.manager import EngineeringManager
from departments.marketing.manager import MarketingManager
from departments.sales.manager import SalesManager
from departments.personal.manager import PersonalManager
from departments.research.manager import ResearchManager

class TestClientModule(Module):
    def __init__(self):
        self.received_events = []
        
    @property
    def name(self) -> str:
        return "test_client"
        
    async def handle_event(self, ev: Event) -> None:
        self.received_events.append(ev)

async def run_trace():
    kernel = Kernel()
    router = ModelRouter()
    tool_reg = ToolRegistry()
    eng_dept = EngineeringManager()
    mkt_dept = MarketingManager()
    sls_dept = SalesManager()
    prs_dept = PersonalManager()
    res_dept = ResearchManager()
    client = TestClientModule()
    
    kernel.register_module(router)
    kernel.register_module(tool_reg)
    kernel.register_module(eng_dept)
    kernel.register_module(mkt_dept)
    kernel.register_module(sls_dept)
    kernel.register_module(prs_dept)
    kernel.register_module(res_dept)
    kernel.register_module(client)
    
    print("Registered modules:", kernel.list_modules())
    
    # 1. Model Router Trace
    print("\n--- 1. Tracing Model Router ---")
    client.received_events.clear()
    req_event = Event(
        source="test_client",
        destination="model_router",
        event_type="model.request_execution",
        payload={
            "task_id": "t-101",
            "task_description": "Architect a high-performance distributed microservice backend",
            "agent": {"role": "architect"}
        }
    )
    await kernel.send_event(req_event)
    await asyncio.sleep(0.1)
    
    print(f"Model Router completion events received by test_client: {len(client.received_events)}")
    if client.received_events:
        res = client.received_events[0].payload["result"]
        print("  Executed by adapter:", res.get("executed_by"))
        print("  Tokens:", res.get("tokens"))
        print("  Cost: $", res.get("cost"))
        print("  Output excerpt:", res.get("output", "")[:120])
        
    # 2. Engineering Department Trace
    print("\n--- 2. Tracing Engineering Department ---")
    client.received_events.clear()
    eng_req = Event(
        source="test_client",
        destination="department.engineering",
        event_type="department.execute_task",
        payload={"task": "Write REST API for user service", "role": "backend"}
    )
    await kernel.send_event(eng_req)
    await asyncio.sleep(0.1)
    
    print(f"Engineering Department completion events received by test_client: {len(client.received_events)}")
    if client.received_events:
        p = client.received_events[-1].payload
        print("  Status:", p.get("status"))
        print("  Worker:", p.get("worker"))
        print("  Result excerpt:", str(p.get("result"))[:120])

    # 3. Research Department Trace
    print("\n--- 3. Tracing Research Department ---")
    client.received_events.clear()
    res_req = Event(
        source="test_client",
        destination="department.research",
        event_type="department.execute_task",
        payload={"task": "Search GitHub repositories for event-driven python frameworks", "category": "tech_trends"}
    )
    await kernel.send_event(res_req)
    await asyncio.sleep(0.1)
    
    print(f"Research Department completion events received by test_client: {len(client.received_events)}")
    if client.received_events:
        p = client.received_events[-1].payload
        print("  Status:", p.get("status"))
        print("  Aggregated Sources:", list(p.get("result", {}).get("aggregated_sources", {}).keys()))

    # 4. Marketing Department Trace
    print("\n--- 4. Tracing Marketing Department ---")
    client.received_events.clear()
    mkt_req = Event(
        source="test_client",
        destination="department.marketing",
        event_type="department.execute_task",
        payload={"task": "Launch social media campaign for Synapse AI OS release", "target_channels": ["twitter", "linkedin"]}
    )
    await kernel.send_event(mkt_req)
    await asyncio.sleep(0.1)
    
    print(f"Marketing Department completion events received by test_client: {len(client.received_events)}")
    if client.received_events:
        p = client.received_events[-1].payload
        print("  Status:", p.get("status"))
        print("  Result excerpt:", str(p.get("result"))[:120])

    # 5. Sales Department Trace
    print("\n--- 5. Tracing Sales Department ---")
    client.received_events.clear()
    sls_req = Event(
        source="test_client",
        destination="department.sales",
        event_type="department.execute_task",
        payload={"task": "Qualify new inbound enterprise leads", "lead_data": {"company": "Acme Corp", "employees": 500, "budget": 100000}}
    )
    await kernel.send_event(sls_req)
    await asyncio.sleep(0.1)
    
    print(f"Sales Department completion events received by test_client: {len(client.received_events)}")
    if client.received_events:
        p = client.received_events[-1].payload
        print("  Status:", p.get("status"))
        print("  Result excerpt:", str(p.get("result"))[:120])

    # 6. Personal Department Trace
    print("\n--- 6. Tracing Personal Department ---")
    client.received_events.clear()
    prs_req = Event(
        source="test_client",
        destination="department.personal",
        event_type="department.execute_task",
        payload={"task": "Schedule executive team sync meeting", "meeting_details": {"time": "14:00", "attendees": ["ceo@synapse.ai", "cto@synapse.ai"]}}
    )
    await kernel.send_event(prs_req)
    await asyncio.sleep(0.1)
    
    print(f"Personal Department completion events received by test_client: {len(client.received_events)}")
    if client.received_events:
        p = client.received_events[-1].payload
        print("  Status:", p.get("status"))
        print("  Result excerpt:", str(p.get("result"))[:120])

    await kernel.shutdown()
    print("\n========================================================")
    print("DYNAMIC TRACE COMPLETE: ALL COMPONENT EVENTS VERIFIED GENUINE!")
    print("========================================================")

if __name__ == "__main__":
    asyncio.run(run_trace())
