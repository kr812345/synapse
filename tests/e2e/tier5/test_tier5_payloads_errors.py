import pytest
import asyncio
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from shared.interfaces import Module, KernelInterface
from shared.models import Event
from kernel.kernel import Kernel
from events.event_bus import EventBus
from tools.tool_registry import ToolRegistry, ToolInterface, PermissionDenied
from registry.sdk.base_agent import BaseAgent
from departments.base import BaseDepartmentModule
from departments.engineering.manager import EngineeringManager
from models.model_router import ModelRouter
from models.cost_tracker import CostTracker
from models.adapters.base import ModelAdapter, ProviderUnavailableError
from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import (
    assert_valid_event,
    assert_valid_cost_tracker_payload,
    create_test_event,
)


# --- Dummy Tools and Agents for Adversarial Testing ---

class SampleTerminalTool(ToolInterface):
    name = "terminal"
    description = "Execute terminal commands"
    parameters = {"command": "str"}
    required_permissions = ["terminal_access"]

    async def execute(self, command: str = "echo hi", **kwargs: Any) -> Any:
        if not isinstance(command, str):
            raise TypeError(f"Command must be string, got {type(command)}")
        return f"Executed: {command}"


class SampleDestructiveTool(ToolInterface):
    name = "delete_repo"
    description = "Destructive repository deletion"
    parameters = {"repo_id": "str"}
    required_permissions = ["admin_delete"]

    async def execute(self, repo_id: str = "", **kwargs: Any) -> Any:
        return f"Deleted repo {repo_id}"


class RestrictedTestAgent(BaseAgent):
    def __init__(self, agent_id: str = "restricted_agent_1", allowed: Optional[List[str]] = None):
        super().__init__(id=agent_id, name="Restricted Agent", department="test", role="worker")
        self._allowed = allowed if allowed is not None else []

    def allowed_tools(self) -> List[str]:
        return self._allowed

    def forbidden_actions(self) -> List[str]:
        return ["delete_repo", "drop_production_db"]

    def memory_access_level(self) -> str:
        return "low"

    def can_handle(self, task_description: str) -> bool:
        return True

    async def execute(self, task: Any) -> Any:
        return {"status": "success"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return None

    def remember(self, knowledge: Any) -> None:
        pass


class CrashingWorker(BaseAgent):
    def __init__(self, agent_id: str = "crashing_worker_1", exception_type: str = "runtime"):
        super().__init__(id=agent_id, name="Crashing Worker", department="test", role="worker")
        self.exception_type = exception_type

    def allowed_tools(self) -> List[str]:
        return []

    def forbidden_actions(self) -> List[str]:
        return []

    def memory_access_level(self) -> str:
        return "low"

    def can_handle(self, task_description: str) -> bool:
        return True

    async def execute(self, task: Any) -> Any:
        if self.exception_type == "zerodiv":
            _ = 1 / 0
        elif self.exception_type == "attribute":
            _ = None.invalid_attribute
        elif self.exception_type == "type":
            _ = "string" + 12345
        else:
            raise RuntimeError("Fatal unhandled worker execution exception!")

    def validate(self, result: Any) -> bool:
        return False

    def report(self) -> Any:
        return None

    def remember(self, knowledge: Any) -> None:
        pass


class FailingSubscriberModule(Module):
    def __init__(self, name: str = "failing_subscriber", exc_msg: str = "Subscriber exploded"):
        self._name = name
        self.exc_msg = exc_msg

    @property
    def name(self) -> str:
        return self._name

    async def handle_event(self, event: Event) -> None:
        raise RuntimeError(self.exc_msg)


class FailingMockAdapter1(ModelAdapter):
    @property
    def name(self) -> str:
        return "Failing Primary Adapter"

    @property
    def model_id(self) -> str:
        return "failing-1"

    @property
    def tier(self) -> str:
        return "tier1"

    @property
    def cost_per_1k_prompt(self) -> float:
        return 0.001

    @property
    def cost_per_1k_completion(self) -> float:
        return 0.002

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        raise ProviderUnavailableError("Primary LLM Adapter HTTP 503 Service Unavailable")


class FailingMockAdapter2(ModelAdapter):
    @property
    def name(self) -> str:
        return "Failing Secondary Adapter"

    @property
    def model_id(self) -> str:
        return "failing-2"

    @property
    def tier(self) -> str:
        return "tier2"

    @property
    def cost_per_1k_prompt(self) -> float:
        return 0.005

    @property
    def cost_per_1k_completion(self) -> float:
        return 0.01

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        raise TimeoutError("Secondary LLM Adapter Read Timeout")


class SuccessMockAdapter3(ModelAdapter):
    @property
    def name(self) -> str:
        return "Successful Tertiary Adapter"

    @property
    def model_id(self) -> str:
        return "success-3"

    @property
    def tier(self) -> str:
        return "tier3"

    @property
    def cost_per_1k_prompt(self) -> float:
        return 0.01

    @property
    def cost_per_1k_completion(self) -> float:
        return 0.03

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        return {
            "output": f"Tertiary successful response for: {prompt}",
            "model_name": self.name,
            "tier": self.tier,
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "total_tokens": 150,
            "cost_usd": 0.0035,
            "raw_response": {}
        }


# ==============================================================================
# TIER 5 ADVERSARIAL STRESS TEST FUNCTIONS
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_unauthorized_tool_execution_direct_and_event(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify unauthorized tool execution raises PermissionDenied directly and emits tool.execution_failed via EventBus."""
    registry = ToolRegistry()
    registry.register(SampleTerminalTool())
    registry.register(SampleDestructiveTool())
    fresh_kernel.register_module(registry)

    # 1. Direct API call with unauthorized agent
    restricted_agent = RestrictedTestAgent(agent_id="agent_no_tools", allowed=[])
    with pytest.raises(PermissionDenied, match="does not have permission to execute terminal"):
        await registry.execute_tool(restricted_agent, "terminal", command="whoami")

    # 2. Event-driven tool execution with unauthorized agent dict payload
    exec_evt = Event(
        source=harness_client.name,
        destination="tool_registry",
        event_type="tool.execute",
        payload={
            "tool_name": "delete_repo",
            "agent": {
                "id": "unauthorized_attacker",
                "allowed_tools": ["safe_read_only_tool"]
            },
            "kwargs": {"repo_id": "production_repo"}
        }
    )

    await fresh_kernel.send_event(exec_evt)

    fail_evt = await harness_client.wait_for_event(event_type="tool.execution_failed")
    assert_valid_event(fail_evt)
    assert fail_evt.payload["tool_name"] == "delete_repo"
    assert fail_evt.payload["status"] == "failed"
    assert "does not have permission" in fail_evt.payload["error"]


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_unknown_tool_name_handling(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify unknown and malicious tool names raise ValueError and emit tool.execution_failed safely."""
    registry = ToolRegistry()
    registry.register(SampleTerminalTool())
    fresh_kernel.register_module(registry)

    agent = RestrictedTestAgent(agent_id="valid_agent", allowed=["terminal"])

    # 1. Direct API call with non-existent tool
    with pytest.raises(ValueError, match="Tool unknown_tool_xyz not found"):
        await registry.execute_tool(agent, "unknown_tool_xyz")

    # 2. Malicious tool names via EventBus
    malicious_names = [
        "../../etc/passwd",
        "terminal; DROP TABLE users;",
        "\x00_null_tool",
        "__proto__",
        "   "
    ]

    for bad_name in malicious_names:
        harness_client.clear()
        evt = Event(
            source=harness_client.name,
            destination="tool_registry",
            event_type="tool.execute",
            payload={
                "tool_name": bad_name,
                "agent": {"id": "valid_agent", "allowed_tools": [bad_name, "terminal"]},
                "kwargs": {}
            }
        )
        await fresh_kernel.send_event(evt)

        fail_evt = await harness_client.wait_for_event(event_type="tool.execution_failed")
        assert fail_evt.payload["status"] == "failed"
        assert f"Tool {bad_name} not found" in fail_evt.payload["error"]


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_invalid_tool_parameters_and_types(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify robust failure handling when tool arguments or payload kwargs types are invalid."""
    registry = ToolRegistry()
    registry.register(SampleTerminalTool())
    fresh_kernel.register_module(registry)

    agent = RestrictedTestAgent(agent_id="authorized_agent", allowed=["terminal"])

    # 1. Direct execution with invalid parameter type (int instead of string for command)
    with pytest.raises(TypeError, match="Command must be string"):
        await registry.execute_tool(agent, "terminal", command=12345)

    # 2. Event payload with kwargs as non-dict (string or None)
    invalid_kwargs_payloads = [
        "invalid_kwargs_string",
        [1, 2, 3],
        None
    ]

    for bad_kwargs in invalid_kwargs_payloads:
        harness_client.clear()
        evt = Event(
            source=harness_client.name,
            destination="tool_registry",
            event_type="tool.execute",
            payload={
                "tool_name": "terminal",
                "agent": {"id": "authorized_agent", "allowed_tools": ["terminal"]},
                "kwargs": bad_kwargs
            }
        )
        await fresh_kernel.send_event(evt)
        # Should either succeed using default kwargs or return execution failure if invalid kwarg unpack fails
        resp_evt = await harness_client.wait_for_event(
            predicate=lambda e: e.event_type in ("tool.execution_result", "tool.execution_failed")
        )
        assert resp_evt.payload["status"] in ("success", "failed")


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_oversized_payloads_and_deep_structures(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify system stability when processing oversized strings and multi-tier nested dictionary payloads."""
    registry = ToolRegistry()
    registry.register(SampleTerminalTool())
    fresh_kernel.register_module(registry)

    # 1MB string payload
    huge_command = "echo " + ("A" * 1_000_000)

    evt = Event(
        source=harness_client.name,
        destination="tool_registry",
        event_type="tool.execute",
        payload={
            "tool_name": "terminal",
            "agent": {"id": "authorized_agent", "allowed_tools": ["terminal"]},
            "kwargs": {"command": huge_command}
        }
    )

    await fresh_kernel.send_event(evt)

    result_evt = await harness_client.wait_for_event(event_type="tool.execution_result", timeout=5.0)
    assert result_evt.payload["status"] == "success"
    assert len(result_evt.payload["result"]) > 1_000_000


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_worker_execution_exception_boundary_isolation(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify worker execution exceptions are caught by BaseDepartmentModule and emit department.task_failed."""
    for exc_type in ["runtime", "zerodiv", "attribute", "type"]:
        crashing_agent = CrashingWorker(agent_id=f"crasher_{exc_type}", exception_type=exc_type)
        dept_module = BaseDepartmentModule(crashing_agent)
        fresh_kernel.register_module(dept_module)

        harness_client.clear()

        task_evt = Event(
            source=harness_client.name,
            destination=dept_module.name,
            event_type="department.execute_task",
            payload={
                "task": {
                    "id": f"task_crash_{exc_type}",
                    "description": "Trigger crash test"
                }
            }
        )

        await fresh_kernel.send_event(task_evt)

        fail_evt = await harness_client.wait_for_event(event_type="department.task_failed")
        assert_valid_event(fail_evt)
        assert fail_evt.payload["task_id"] == f"task_crash_{exc_type}"
        assert fail_evt.payload["status"] == "failed"
        assert len(fail_evt.payload["error"]) > 0

        # Unregister crasher to keep kernel clean for next iteration
        fresh_kernel.unregister_module(dept_module.name)

    # Verify kernel health status after processing multiple worker crashes
    health = fresh_kernel.get_health_status()
    assert health["status"] == "healthy"


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_subscriber_exception_isolation_under_broadcast_and_unicast(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify subscriber exceptions in unicast and broadcast routing do not crash EventBus or block healthy subscribers."""
    sub_fail_1 = FailingSubscriberModule("sub_fail_1", "Fatal DB connection dropped")
    sub_fail_2 = FailingSubscriberModule("sub_fail_2", "ZeroDivisionError in handler")

    fresh_kernel.register_module(sub_fail_1)
    fresh_kernel.register_module(sub_fail_2)

    bus = fresh_kernel.event_bus

    # 1. Unicast to failing subscriber
    unicast_evt = Event(
        source=harness_client.name,
        destination="sub_fail_1",
        event_type="test.unicast",
        payload={"data": "test"}
    )
    await fresh_kernel.send_event(unicast_evt)

    # Dead letter queue should record unicast exception
    dlq = bus.get_dead_letters()
    assert len(dlq) == 1
    assert "Handler exception in module 'sub_fail_1'" in dlq[0]["reason"]

    bus.clear_dead_letters()

    # 2. Broadcast to all subscribers (*)
    broadcast_evt = Event(
        source="system",
        destination="*",
        event_type="system.broadcast_alert",
        payload={"alert": "global_notice"}
    )
    await fresh_kernel.send_event(broadcast_evt)

    # Healthy harness module receives the broadcast event cleanly
    received = await harness_client.wait_for_event(event_type="system.broadcast_alert")
    assert received.payload["alert"] == "global_notice"

    # Both failing subscribers recorded errors in DLQ
    dlq_broadcast = bus.get_dead_letters()
    assert len(dlq_broadcast) == 2
    failing_module_names = [item["reason"] for item in dlq_broadcast]
    assert any("sub_fail_1" in name for name in failing_module_names)
    assert any("sub_fail_2" in name for name in failing_module_names)

    # Verify event bus stats counter
    stats = bus.get_stats()
    assert stats["errors"] == 3


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_model_router_primary_and_secondary_adapter_failure_fallback():
    """Verify multi-tier LLM fallback redundancy when primary and secondary adapters raise exceptions."""
    primary = FailingMockAdapter1()
    secondary = FailingMockAdapter2()
    tertiary = SuccessMockAdapter3()

    router = ModelRouter(adapters=[primary, secondary, tertiary])

    res = await router.generate_with_fallback("Perform deep architectural optimization")

    assert res["model_name"] == "Successful Tertiary Adapter"
    assert res["tier"] == "tier3"
    assert "Tertiary successful response" in res["output"]


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_model_router_all_adapters_failing_catastrophic_error_isolation(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify ModelRouter returns model.execution_complete with status=error when all adapters fail."""
    primary = FailingMockAdapter1()
    secondary = FailingMockAdapter2()

    router = ModelRouter(adapters=[primary, secondary])
    fresh_kernel.register_module(router)

    evt = Event(
        source=harness_client.name,
        destination="model_router",
        event_type="model.request_execution",
        payload={
            "task_id": "task_all_fail_99",
            "task_description": "Complex task requiring failing models",
            "agent": {"identity": "test_agent"}
        }
    )

    await fresh_kernel.send_event(evt)

    completed_evt = await harness_client.wait_for_event(event_type="model.execution_complete")
    assert_valid_event(completed_evt)

    res = completed_evt.payload["result"]
    assert res["status"] == "error"
    assert "Execution failed" in res["output"]
    assert res["cost"] == 0.0
    assert res["tokens"]["total_tokens"] == 0
    assert_valid_cost_tracker_payload(res)


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_model_router_empty_prompt_and_none_description_handling(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify ModelRouter and decide_model handle empty prompts, whitespace, and None descriptions cleanly."""
    router = ModelRouter()
    fresh_kernel.register_module(router)

    # 1. Direct decide_model calls
    adapter_empty = router.decide_model("", payload={})
    assert adapter_empty.tier == "tier1"

    adapter_ws = router.decide_model("    \t\n  ", payload={})
    assert adapter_ws.tier == "tier1"

    adapter_none = router.decide_model(None, payload={})
    assert adapter_none.tier == "tier1"

    # 2. Event with task_description missing or None
    harness_client.clear()
    evt_none_desc = Event(
        source=harness_client.name,
        destination="model_router",
        event_type="model.request_execution",
        payload={
            "task_id": "task_none_desc_1",
            "task_description": None,
            "agent": None
        }
    )

    await fresh_kernel.send_event(evt_none_desc)

    comp_evt = await harness_client.wait_for_event(event_type="model.execution_complete")
    res = comp_evt.payload["result"]
    assert res["status"] == "success"
    assert res["agent"] == "unknown"


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_cost_tracker_zero_token_negative_token_and_null_agent_edge_cases():
    """Verify CostTracker handling of zero tokens, negative inputs, null IDs, and aggregate breakdowns."""
    tracker = CostTracker()

    # Null agent & task_id with negative tokens
    rec = tracker.record_usage(
        task_id=None,
        agent=None,
        model_name="Gemini Flash",
        tier="tier1",
        prompt_tokens=-500,
        completion_tokens=-200,
        cost_usd=-12.34
    )

    assert rec["task_id"] == "unknown"
    assert rec["agent"] == "unknown"
    assert rec["prompt_tokens"] == 0
    assert rec["completion_tokens"] == 0
    assert rec["total_tokens"] == 0
    assert rec["cost_usd"] == 0.0

    summary = tracker.get_summary()
    assert summary["total_cost_usd"] == 0.0
    assert summary["request_count"] == 1

    tier_bd = tracker.get_tier_breakdown()
    assert "tier1" in tier_bd
    assert tier_bd["tier1"]["request_count"] == 1

    agent_bd = tracker.get_agent_breakdown()
    assert "unknown" in agent_bd
    assert agent_bd["unknown"]["request_count"] == 1


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_concurrent_adversarial_payload_flooding(fresh_kernel: Kernel):
    """Verify Kernel and EventBus stability under high-concurrency stream of mixed adversarial payloads."""
    registry = ToolRegistry()
    registry.register(SampleTerminalTool())
    fresh_kernel.register_module(registry)

    sub_fail = FailingSubscriberModule("flooding_crasher")
    fresh_kernel.register_module(sub_fail)

    harness = OpaqueTestHarness("flood_harness")
    fresh_kernel.register_module(harness)

    async def fire_adversarial_event(index: int):
        if index % 4 == 0:
            # Unauthorized / unknown tool execution
            evt = Event(
                source=harness.name,
                destination="tool_registry",
                event_type="tool.execute",
                payload={"tool_name": f"unauthorized_tool_{index}", "agent": {"allowed_tools": []}}
            )
        elif index % 4 == 1:
            # Event directed to crashing subscriber
            evt = Event(
                source=harness.name,
                destination="flooding_crasher",
                event_type="test.crash",
                payload={"seq": index}
            )
        elif index % 4 == 2:
            # Malformed event with missing fields
            evt = Event(
                source=harness.name,
                destination="nonexistent_module",
                event_type="test.unroutable",
                payload={}
            )
        else:
            # Valid unicast event to harness
            evt = Event(
                source="flood_producer",
                destination=harness.name,
                event_type="test.valid",
                payload={"seq": index}
            )
        await fresh_kernel.send_event(evt)

    # Launch 60 concurrent event send operations
    await asyncio.gather(*[fire_adversarial_event(i) for i in range(60)])
    await asyncio.sleep(0.1)

    # Verify kernel remains healthy and valid events were processed
    health = fresh_kernel.get_health_status()
    assert health["status"] == "healthy"
    assert len(harness.received_events) >= 15

    # Clean shutdown
    await fresh_kernel.shutdown()


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_tool_registry_duplicate_registration_and_edge_cases(fresh_kernel: Kernel):
    """Verify ToolRegistry handling of duplicate tool registration, non-existent lookup, and non-callable allowed_tools."""
    registry = ToolRegistry()
    
    tool1 = SampleTerminalTool()
    class DuplicateTerminalTool(ToolInterface):
        name = "terminal"
        description = "Overriding terminal tool"
        parameters = {}
        required_permissions = []
        async def execute(self, **kwargs: Any) -> Any:
            return "Overridden execute"

    registry.register(tool1)
    assert registry.get_tool("terminal").description == "Execute terminal commands"

    # Re-register with same name overrides previous registration safely
    registry.register(DuplicateTerminalTool())
    assert registry.get_tool("terminal").description == "Overriding terminal tool"
    assert registry.get_tool("non_existent_tool_abc") is None

    class StaticAllowedAgent:
        id = "static_agent"
        allowed_tools = ["terminal"]

    agent_static = StaticAllowedAgent()
    res = await registry.execute_tool(agent_static, "terminal")
    assert res == "Overridden execute"


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_model_router_malformed_agent_and_payload_types(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify ModelRouter event handling when agent payload is a non-dict scalar or list."""
    router = ModelRouter()
    fresh_kernel.register_module(router)

    malformed_agents = [
        ["agent_list_item1", "agent_list_item2"],
        12345,
        True,
        "string_agent_identity"
    ]

    for bad_agent in malformed_agents:
        harness_client.clear()
        evt = Event(
            source=harness_client.name,
            destination="model_router",
            event_type="model.request_execution",
            payload={
                "task_id": f"task_bad_agent_{type(bad_agent).__name__}",
                "task_description": "Summarize release notes",
                "agent": bad_agent
            }
        )
        await fresh_kernel.send_event(evt)

        comp_evt = await harness_client.wait_for_event(event_type="model.execution_complete")
        assert comp_evt.payload["result"]["status"] == "success"
        assert len(comp_evt.payload["result"]["agent"]) > 0

