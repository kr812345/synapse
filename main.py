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
        import uuid
        
        session_id = f"chat_session_{uuid.uuid4().hex[:8]}"
        
        class ChatBridge(Module):
            def __init__(self):
                self.kernel = None
                self.response_received = asyncio.Event()
                self.history_received = asyncio.Event()
                self.latest_response = ""
                self.history_data = []
                
            @property
            def name(self) -> str:
                return "cli_chat"
                
            def set_kernel(self, kernel):
                self.kernel = kernel
                
            async def handle_event(self, event: Event) -> None:
                if event.destination == "cli_chat":
                    if event.event_type == "task.complete":
                        self.latest_response = event.payload.get('result', "Task done.")
                        self.response_received.set()
                    elif event.event_type == "memory.chat_history_result":
                        self.history_data = event.payload.get('history', [])
                        self.history_received.set()

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
                    
                    # Store user message
                    await kernel.send_event(Event(
                        source="cli_chat", destination="memory_engine", event_type="memory.store_chat",
                        payload={"session_id": session_id, "role": "user", "content": user_input}
                    ))
                    
                    # Fetch history
                    chat_bridge.history_received.clear()
                    await kernel.send_event(Event(
                        source="cli_chat", destination="memory_engine", event_type="memory.get_chat_history",
                        payload={"session_id": session_id}
                    ))
                    await chat_bridge.history_received.wait()
                    
                    # Build contextual task
                    context_str = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_bridge.history_data])
                    full_task_desc = f"Conversation History:\n{context_str}\n\nTask:\n{user_input}"
                    
                    # Send event to OS
                    chat_bridge.response_received.clear()
                    task_event = Event(
                        source="cli_chat",
                        destination="scheduler",
                        event_type="task.create",
                        payload={"task": {"id": f"chat_{int(time.time())}", "description": full_task_desc, "requester": "cli_chat"}}
                    )
                    await kernel.send_event(task_event)
                    
                    # Wait for OS to process
                    await chat_bridge.response_received.wait()
                    
                    # Extract final text output
                    final_output_text = str(chat_bridge.latest_response)
                    if isinstance(chat_bridge.latest_response, dict) and 'output' in chat_bridge.latest_response:
                        final_output_text = str(chat_bridge.latest_response['output'])
                        
                    # Store assistant message
                    await kernel.send_event(Event(
                        source="cli_chat", destination="memory_engine", event_type="memory.store_chat",
                        payload={"session_id": session_id, "role": "assistant", "content": final_output_text}
                    ))
                    
                    avatar.state = "happy"
                    live.update(avatar.get_renderable())
                    time.sleep(0.5)
                    avatar.state = "idle"
                    live.update(avatar.get_renderable())
                    
                console.print("[bold green]Synapse:[/bold green]")
                if isinstance(chat_bridge.latest_response, dict) and 'output' in chat_bridge.latest_response:
                    console.print(Markdown(str(chat_bridge.latest_response['output'])))
                else:
                    console.print(Markdown(str(chat_bridge.latest_response)))
                
            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold cyan]Synapse:[/bold cyan] Shutting down OS... Goodbye!")
                break
                
    asyncio.run(_run_chat())

@app.command()
def listen():
    """Start Voice Mode to talk to Synapse via your microphone."""
    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger('events').setLevel(logging.WARNING)
    logging.getLogger('kernel').setLevel(logging.WARNING)
    logging.getLogger('scheduler').setLevel(logging.WARNING)
    logging.getLogger('agents').setLevel(logging.WARNING)
    logging.getLogger('models').setLevel(logging.WARNING)
    
    console = Console()
    console.clear()
    
    try:
        import speech_recognition as sr
    except ImportError:
        console.print("[bold red]Error:[/bold red] The speech_recognition library is not installed.")
        console.print("Please run: [bold cyan].venv/bin/pip install SpeechRecognition pyaudio[/bold cyan]")
        return
        
    avatar = SynapseAvatar()
    
    async def _run_listen():
        kernel, registry, scheduler = await boot_os_with_bridge()
        from shared.interfaces import Module
        import uuid
        
        session_id = f"voice_session_{uuid.uuid4().hex[:8]}"
        
        class VoiceBridge(Module):
            def __init__(self):
                self.kernel = None
                self.response_received = asyncio.Event()
                self.latest_response = ""
                
            @property
            def name(self) -> str:
                return "cli_voice"
                
            def set_kernel(self, kernel):
                self.kernel = kernel
                
            async def handle_event(self, event: Event) -> None:
                if event.destination == "cli_voice" and event.event_type == "task.complete":
                    self.latest_response = event.payload.get('result', "Task done.")
                    self.response_received.set()

        voice_bridge = VoiceBridge()
        kernel.register_module(voice_bridge)
        
        r = sr.Recognizer()
        
        # Disable dynamic energy threshold to prevent it from getting stuck
        r.dynamic_energy_threshold = False
        r.energy_threshold = 400
        
        try:
            mic = sr.Microphone()
        except OSError as e:
            console.print(f"[bold red]Microphone Error:[/bold red] Could not find or access a microphone on your system. ({e})")
            return
            
        with mic as source:
            console.print("\n[bold green]Synapse OS Voice Mode[/bold green] (Press Ctrl+C to exit)")
            console.print("Calibrating ambient noise...")
            r.adjust_for_ambient_noise(source, duration=1)
            
            while True:
                try:
                    with Live(avatar.get_renderable(), refresh_per_second=10, console=console) as live:
                        avatar.state = "idle"
                        live.update(avatar.get_renderable())
                        
                        console.print("\n[bold cyan]Listening... (speak now)[/bold cyan]")
                        audio = r.listen(source, timeout=10, phrase_time_limit=15)
                        
                        avatar.state = "thinking"
                        live.update(avatar.get_renderable())
                        
                        console.print("[dim]Transcribing audio...[/dim]")
                        try:
                            # Using Google's free recognition for zero-setup
                            user_input = r.recognize_google(audio)
                            console.print(f"\n[bold green]You said:[/bold green] {user_input}")
                            
                            # Send to OS
                            voice_bridge.response_received.clear()
                            task_event = Event(
                                source="cli_voice",
                                destination="scheduler",
                                event_type="task.create",
                                payload={"task": {"id": f"voice_{int(time.time())}", "description": user_input, "requester": "cli_voice"}}
                            )
                            await kernel.send_event(task_event)
                            
                            await voice_bridge.response_received.wait()
                            
                            avatar.state = "happy"
                            live.update(avatar.get_renderable())
                            time.sleep(1)
                            
                            console.print("\n[bold magenta]Synapse:[/bold magenta]")
                            if isinstance(voice_bridge.latest_response, dict) and 'output' in voice_bridge.latest_response:
                                console.print(Markdown(str(voice_bridge.latest_response['output'])))
                            else:
                                console.print(Markdown(str(voice_bridge.latest_response)))
                                
                        except sr.UnknownValueError:
                            console.print("[dim]Sorry, I didn't catch that.[/dim]")
                        except sr.RequestError as e:
                            console.print(f"[bold red]Speech API Error:[/bold red] {e}")
                            
                except sr.WaitTimeoutError:
                    continue
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[bold cyan]Exiting Voice Mode... Goodbye![/bold cyan]")
                    break
                    
    asyncio.run(_run_listen())

if __name__ == "__main__":
    app()
