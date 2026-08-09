import pytest
import asyncio
import importlib
from typing import List, Optional, Callable, Dict, Any, Tuple

from shared.interfaces import Module, KernelInterface
from shared.models import Event
from kernel.kernel import Kernel
from models.model_router import ModelRouter
from agents.registry import AgentRegistry
from scheduler.scheduler import Scheduler
from memory.memory_engine import MemoryEngine
from departments.echo.echo_manager import EchoDepartment


class OpaqueTestHarness(Module):
    """
    Opaque-box testing harness module for Synapse AI OS.
    Intercepts, records, and provides deterministic event synchronization
    for asynchronous system events via asyncio.Event without brittle sleep calls.
    """
    def __init__(self, name: str = "opaque_harness"):
        self._name = name
        self.kernel: Optional[KernelInterface] = None
        self.received_events: List[Event] = []
        self._event_listeners: List[Tuple[Callable[[Event], bool], asyncio.Event]] = []

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        """Record received event and trigger matching event listeners."""
        self.received_events.append(event)
        # Notify active event listeners
        for predicate, signal in list(self._event_listeners):
            try:
                if predicate(event):
                    signal.set()
            except Exception:
                pass

    async def wait_for_event(
        self,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        predicate: Optional[Callable[[Event], bool]] = None,
        timeout: float = 3.0
    ) -> Event:
        """
        Deterministically wait for an event matching specified criteria.
        Checks historical received events first, then registers an async listener.
        """
        def match_fn(e: Event) -> bool:
            if event_type is not None and e.event_type != event_type:
                return False
            if source is not None and e.source != source:
                return False
            if predicate is not None and not predicate(e):
                return False
            return True

        # Check previously captured events first
        for e in self.received_events:
            if match_fn(e):
                return e

        # Register listener for future events
        signal = asyncio.Event()
        listener_tuple = (match_fn, signal)
        self._event_listeners.append(listener_tuple)

        try:
            await asyncio.wait_for(signal.wait(), timeout=timeout)
            for e in reversed(self.received_events):
                if match_fn(e):
                    return e
            raise RuntimeError("Event signal set but event not found in received list")
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                f"Timed out waiting {timeout}s for event (event_type={event_type}, source={source})"
            )
        finally:
            if listener_tuple in self._event_listeners:
                self._event_listeners.remove(listener_tuple)

    def clear(self) -> None:
        """Clear recorded events and active listeners."""
        self.received_events.clear()
        self._event_listeners.clear()


@pytest.fixture
def fresh_kernel() -> Kernel:
    """Fixture providing a fresh, isolated Kernel control plane."""
    return Kernel()


@pytest.fixture
def harness_client(fresh_kernel: Kernel) -> OpaqueTestHarness:
    """Fixture registering and returning an OpaqueTestHarness instance attached to fresh_kernel."""
    harness = OpaqueTestHarness(name="harness_client")
    fresh_kernel.register_module(harness)
    return harness


@pytest.fixture
def full_os_kernel(fresh_kernel: Kernel) -> Kernel:
    """Fixture registering all core infrastructure modules and available department modules into Kernel."""
    infra_modules = [
        ModelRouter(),
        AgentRegistry(),
        Scheduler(),
        MemoryEngine(),
        EchoDepartment()
    ]
    for module in infra_modules:
        fresh_kernel.register_module(module)

    # Dynamically register department modules if they implement Module interface
    dept_specs = [
        ("departments.engineering.manager", "EngineeringManager", ("eng_mgr", "Engineering Manager")),
        ("departments.research.manager", "ResearchManager", ()),
        ("departments.marketing.manager", "MarketingManager", ("mkt_mgr", "Marketing Manager")),
        ("departments.personal.manager", "PersonalManager", ("prs_mgr", "Personal Manager")),
        ("departments.sales.manager", "SalesManager", ("sls_mgr", "Sales Manager")),
    ]
    for mod_path, cls_name, args in dept_specs:
        try:
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name)
            obj = cls(*args)
            if isinstance(obj, Module):
                fresh_kernel.register_module(obj)
        except Exception:
            pass

    return fresh_kernel


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Pytest terminal summary hook displaying clean Tier Coverage Statistics."""
    stats = terminalreporter.stats
    reports = []
    for key in ("passed", "failed", "skipped", "xfailed"):
        for rep in stats.get(key, []):
            if rep.when == "call":
                reports.append(rep)

    if not reports:
        return

    tier_counts = {
        "Tier 1": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
        "Tier 2": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
        "Tier 3": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
        "Tier 4": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
        "Tier 5": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
        "Other":  {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
    }

    for rep in reports:
        tier_name = "Other"
        kw = rep.keywords
        nodeid = rep.nodeid.lower()
        if "tier1" in kw or "tier1" in nodeid:
            tier_name = "Tier 1"
        elif "tier2" in kw or "tier2" in nodeid:
            tier_name = "Tier 2"
        elif "tier3" in kw or "tier3" in nodeid:
            tier_name = "Tier 3"
        elif "tier4" in kw or "tier4" in nodeid:
            tier_name = "Tier 4"
        elif "tier5" in kw or "tier5" in nodeid:
            tier_name = "Tier 5"

        tier_counts[tier_name]["total"] += 1
        if rep.outcome == "passed":
            tier_counts[tier_name]["passed"] += 1
        elif rep.outcome == "failed":
            tier_counts[tier_name]["failed"] += 1
        else:
            tier_counts[tier_name]["skipped"] += 1

    terminalreporter.write_line("\n" + "=" * 80)
    terminalreporter.write_line("                  SYNAPSE AI OS — TIER COVERAGE STATISTICS              ")
    terminalreporter.write_line("=" * 80)
    terminalreporter.write_line(f"{'Tier':<10} | {'Total':<8} | {'Passed':<8} | {'Failed':<8} | {'Skipped':<8} | {'Pass %':<8}")
    terminalreporter.write_line("-" * 80)

    grand_total = 0
    grand_passed = 0
    grand_failed = 0
    grand_skipped = 0

    for tier, data in tier_counts.items():
        if data["total"] == 0:
            continue
        grand_total += data["total"]
        grand_passed += data["passed"]
        grand_failed += data["failed"]
        grand_skipped += data["skipped"]
        pass_pct = (data["passed"] / data["total"] * 100.0) if data["total"] > 0 else 0.0
        terminalreporter.write_line(
            f"{tier:<10} | {data['total']:<8} | {data['passed']:<8} | {data['failed']:<8} | {data['skipped']:<8} | {pass_pct:>6.1f}%"
        )

    terminalreporter.write_line("-" * 80)
    overall_pct = (grand_passed / grand_total * 100.0) if grand_total > 0 else 0.0
    terminalreporter.write_line(
        f"{'TOTAL':<10} | {grand_total:<8} | {grand_passed:<8} | {grand_failed:<8} | {grand_skipped:<8} | {overall_pct:>6.1f}%"
    )
    terminalreporter.write_line("=" * 80 + "\n")
