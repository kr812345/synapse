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
    
    tool_registry = ToolRegistry()
    tool_registry.register(GitHubTool())
    tool_registry.register(RedditTool())
    tool_registry.register(BrowserTool())
    
    from api.server import bridge
    kernel.register_module(memory)
    kernel.register_module(registry)
    kernel.register_module(router)
    kernel.register_module(scheduler)
    kernel.register_module(bridge)
    
    # Register departments
    registry.register_agent(ResearchManager("rm_1", "Research Manager"))
    registry.register_agent(EngineeringManager("eng_1", "Engineering Manager"))
    registry.register_agent(MarketingManager("mkt_1", "Marketing Manager"))
    registry.register_agent(PersonalManager("per_1", "Personal Manager"))
    
    print("[SYSTEM] Synapse OS Booted Successfully.")
    return kernel, registry, scheduler

@app.command()
def execute(task: str):
    """Execute a task using the OS Event Bus."""
    async def _run():
        kernel, registry, scheduler = await boot_os()
        
        print(f"[USER] Task: {task}")
        
        # Dispatch task to the system via the Event Bus
        task_event = Event(
            source="cli",
            destination="task_scheduler",
            event_type="scheduler.new_task",
            payload={"description": task, "task_id": "cli_task_1"}
        )
        await kernel.send_event(task_event)
        
        # Wait a bit to simulate execution
        for _ in range(5):
            await asyncio.sleep(1)
            print("[SYSTEM] OS Processing Event Bus...")
            
    asyncio.run(_run())

@app.command()
def serve():
    """Boot the OS and start the WebSocket server (Simulated output for now, start API via uvicorn)."""
    print("[SYSTEM] Start the API via: uvicorn api.server:app --reload")

if __name__ == "__main__":
    app()
