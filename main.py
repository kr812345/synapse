import asyncio
import typer
import json
from kernel.kernel import Kernel
from memory.memory_engine import MemoryEngine
from agents.registry import AgentRegistry
from models.model_router import ModelRouter
from scheduler.scheduler import Scheduler
from departments.research.manager import ResearchManager
from departments.engineering.manager import EngineeringManager
from departments.marketing.manager import MarketingManager
from departments.personal.manager import PersonalManager
from shared.models import Event
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

app = typer.Typer(help="Synapse AI OS CLI")

async def boot_os():
    kernel = Kernel()
    memory = MemoryEngine(db_url="dbname=synapse user=root")
    registry = AgentRegistry()
    router = ModelRouter()
    scheduler = Scheduler()
    
    from tools.tool_registry import ToolRegistry
    from tools.library.github_tool import GitHubTool
    from tools.library.reddit_tool import RedditTool
    from tools.library.browser_tool import BrowserTool
    from tools.library.email_tool import EmailTool
    from tools.library.pdf_tool import PDFTool
    
    tool_registry = ToolRegistry()
    tool_registry.register(GitHubTool())
    tool_registry.register(RedditTool())
    tool_registry.register(BrowserTool())
    tool_registry.register(EmailTool())
    tool_registry.register(PDFTool())
    
    from api.server import bridge
    kernel.register_module(memory)
    kernel.register_module(registry)
    kernel.register_module(router)
    kernel.register_module(scheduler)
    kernel.register_module(bridge)
    
    from departments.base import BaseDepartmentModule
    from shared.models import AgentContract

    # Instantiate managers
    rm = ResearchManager("rm_1", "Research Manager")
    eng = EngineeringManager("eng_1", "Engineering Manager")
    mkt = MarketingManager("mkt_1", "Marketing Manager")
    per = PersonalManager("per_1", "Personal Manager")

    # Register as Kernel Modules (via BaseDepartmentModule)
    kernel.register_module(BaseDepartmentModule(rm))
    kernel.register_module(BaseDepartmentModule(eng))
    kernel.register_module(BaseDepartmentModule(mkt))
    kernel.register_module(BaseDepartmentModule(per))

    # Register their Contracts to AgentRegistry
    def make_contract(agent):
        return AgentContract(
            identity=agent.id,
            department=agent.department,
            goal=f"Manage {agent.department}",
            responsibilities=["execute", "delegate"],
            forbidden_actions=agent.forbidden_actions(),
            allowed_tools=agent.allowed_tools(),
            memory_access=agent.memory_access_level(),
            output_schema={},
            confidence_score=agent.confidence_score
        )

    registry.register_agent(make_contract(rm))
    registry.register_agent(make_contract(eng))
    registry.register_agent(make_contract(mkt))
    registry.register_agent(make_contract(per))
    
    print("[SYSTEM] Synapse OS Booted Successfully.")
    return kernel, registry, scheduler

@app.command()
def execute(task: str):
    """Execute a task using the OS Event Bus."""
    async def _run():
        kernel, registry, scheduler = await boot_os()
        
        print(f"[USER] Task: {task}")
        
        from shared.interfaces import Module
        
        class CLIBridge(Module):
            def __init__(self):
                self.kernel = None
                self.task_done = asyncio.Event()
                
            @property
            def name(self) -> str:
                return "cli"
                
            def set_kernel(self, kernel):
                self.kernel = kernel
                
            async def handle_event(self, event: Event) -> None:
                if event.destination == "cli" and event.event_type == "task.complete":
                    print(f"\n[SYSTEM] Task Completed! Result:\n{event.payload.get('result')}\n")
                    self.task_done.set()

        cli_bridge = CLIBridge()
        kernel.register_module(cli_bridge)

        # Dispatch task to the system via the Event Bus
        task_event = Event(
            source="cli",
            destination="scheduler",
            event_type="task.create",
            payload={"task": {"id": "cli_task_1", "description": task, "requester": "cli"}}
        )
        await kernel.send_event(task_event)
        
        print("[SYSTEM] OS Processing Event Bus... waiting for completion...")
        await cli_bridge.task_done.wait()
        
    asyncio.run(_run())

@app.command()
def serve():
    """Boot the OS and start the WebSocket server (Simulated output for now, start API via uvicorn)."""
    print("[SYSTEM] Start the API via: uvicorn api.server:app --reload")

if __name__ == "__main__":
    app()
