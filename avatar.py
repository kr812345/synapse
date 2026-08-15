import time
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text

class SynapseAvatar:
    def __init__(self):
        self.state = "idle"
        
    def get_renderable(self):
        # A simple animated ANSI art face that changes based on state
        if self.state == "idle":
            face = "[bold cyan][ ^ _ ^ ][/bold cyan]"
            status = "Waiting..."
        elif self.state == "thinking":
            face = "[bold magenta][ > _ < ][/bold magenta]"
            status = "Thinking..."
        elif self.state == "happy":
            face = "[bold green][ ★ ᴗ ★ ][/bold green]"
            status = "Solved!"
        elif self.state == "confused":
            face = "[bold yellow][ @ _ @ ][/bold yellow]"
            status = "Confused..."
        else:
            face = "[bold cyan][ • _ • ][/bold cyan]"
            status = "..."
            
        # Compose the avatar UI block
        content = f"{face}\n[dim]{status}[/dim]"
        
        return Panel(
            Align.center(Text.from_markup(content)), 
            title="[bold blue]Synapse[/bold blue]", 
            border_style="cyan",
            padding=(1, 2),
            width=25
        )
