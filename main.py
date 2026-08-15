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
from boot import boot_os

app = typer.Typer(help="Synapse AI OS CLI")

async def boot_os_with_bridge():
    kernel, registry, scheduler = await boot_os()
    from api.server import bridge
    kernel.register_module(bridge)
    return kernel, registry, scheduler

import logging

@app.command()
def execute(task: str):
    """Execute a one-off task using the OS Event Bus with the Avatar interface."""
    # Suppress all those INFO logs from the OS backend!
    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger('events').setLevel(logging.WARNING)
    logging.getLogger('kernel').setLevel(logging.WARNING)
    logging.getLogger('scheduler').setLevel(logging.WARNING)
    logging.getLogger('agents').setLevel(logging.WARNING)
    logging.getLogger('models').setLevel(logging.WARNING)
    
    console = Console()
    console.clear()
    avatar = SynapseAvatar()
    
    async def _run():
        with Live(avatar.get_renderable(), refresh_per_second=10, console=console) as live:
            avatar.state = "thinking"
            live.update(avatar.get_renderable())
            
            kernel, registry, scheduler = await boot_os_with_bridge()
            from shared.interfaces import Module
            
            class ExecuteBridge(Module):
                def __init__(self):
                    self.kernel = None
                    self.task_done = asyncio.Event()
                    self.final_result = None
                    
                @property
                def name(self) -> str:
                    return "cli"
                    
                def set_kernel(self, kernel):
                    self.kernel = kernel
                    
                async def handle_event(self, event: Event) -> None:
                    if event.destination == "cli" and event.event_type == "task.complete":
                        self.final_result = event.payload.get('result')
                        self.task_done.set()

            cli_bridge = ExecuteBridge()
            kernel.register_module(cli_bridge)

            # Dispatch task to the system via the Event Bus
            import time
            task_event = Event(
                source="cli",
                destination="scheduler",
                event_type="task.create",
                payload={"task": {"id": f"cli_task_{int(time.time())}", "description": task, "requester": "cli"}}
            )
            await kernel.send_event(task_event)
            
            # Wait for completion while the avatar is "thinking"
            await cli_bridge.task_done.wait()
            
            avatar.state = "happy"
            live.update(avatar.get_renderable())
            time.sleep(0.5)
            avatar.state = "idle"
            live.update(avatar.get_renderable())
            
        # Outside of Live block, print the final markdown result
        console.print("[bold green]Synapse:[/bold green]")
        
        # Format the output beautifully instead of dumping raw JSON
        if isinstance(cli_bridge.final_result, dict) and 'output' in cli_bridge.final_result:
            console.print(Markdown(str(cli_bridge.final_result['output'])))
        else:
            console.print(Markdown(str(cli_bridge.final_result)))
            
    asyncio.run(_run())

@app.command()
def serve():
    """Boot the OS and start the WebSocket server (Simulated output for now, start API via uvicorn)."""
    print("[SYSTEM] Start the API via: uvicorn api.server:app --reload")

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from avatar import SynapseAvatar
import time

@app.command()
def chat():
    """Start an interactive chat session with Synapse OS."""
    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger('events').setLevel(logging.WARNING)
    logging.getLogger('kernel').setLevel(logging.WARNING)
    logging.getLogger('scheduler').setLevel(logging.WARNING)
    logging.getLogger('agents').setLevel(logging.WARNING)
    logging.getLogger('models').setLevel(logging.WARNING)
    
    console = Console()
    console.clear()
    
    avatar = SynapseAvatar()
    
    # Intro animation
    with Live(avatar.get_renderable(), refresh_per_second=10, console=console) as live:
        time.sleep(1)
        avatar.state = "thinking"
        live.update(avatar.get_renderable())
        time.sleep(1)
        avatar.state = "happy"
        live.update(avatar.get_renderable())
        time.sleep(0.5)
        avatar.state = "idle"
        live.update(avatar.get_renderable())
        
    console.print("\n[bold green]Synapse OS:[/bold green] Booting system... Ready.")
    
    async def _run_chat():
        kernel, registry, scheduler = await boot_os_with_bridge()
        from shared.interfaces import Module
        
        class ChatBridge(Module):
            def __init__(self):
                self.kernel = None
                self.response_received = asyncio.Event()
                self.latest_response = ""
                
            @property
            def name(self) -> str:
                return "cli_chat"
                
            def set_kernel(self, kernel):
                self.kernel = kernel
                
            async def handle_event(self, event: Event) -> None:
                if event.destination == "cli_chat" and event.event_type == "task.complete":
                    self.latest_response = event.payload.get('result', "Task done.")
                    self.response_received.set()

        chat_bridge = ChatBridge()
        kernel.register_module(chat_bridge)
        
        while True:
            try:
                user_input = input("\nYou: ")
                if user_input.lower() in ['exit', 'quit']:
                    console.print("[bold cyan]Synapse:[/bold cyan] Goodbye! [ ^ _ ^ ]")
                    break
                    
                with Live(avatar.get_renderable(), refresh_per_second=10, console=console) as live:
                    avatar.state = "thinking"
                    live.update(avatar.get_renderable())
                    
                    # Send event to OS
                    chat_bridge.response_received.clear()
                    task_event = Event(
                        source="cli_chat",
                        destination="scheduler",
                        event_type="task.create",
                        payload={"task": {"id": f"chat_{int(time.time())}", "description": user_input, "requester": "cli_chat"}}
                    )
                    await kernel.send_event(task_event)
                    
                    # Wait for OS to process
                    await chat_bridge.response_received.wait()
                    
                    avatar.state = "happy"
                    live.update(avatar.get_renderable())
                    time.sleep(0.5)
                    avatar.state = "idle"
                    live.update(avatar.get_renderable())
                    
                console.print("[bold green]Synapse:[/bold green]")
                console.print(Markdown(str(chat_bridge.latest_response)))
                
            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold cyan]Synapse:[/bold cyan] Shutting down OS... Goodbye!")
                break
                
    asyncio.run(_run_chat())

if __name__ == "__main__":
    app()
