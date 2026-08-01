from tools.tool_registry import ToolInterface
from typing import Any

class BrowserTool(ToolInterface):
    name = "browser"
    description = "Headless scraping and DOM reading."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to scrape"}
        },
        "required": ["url"]
    }
    required_permissions = ["web_read"]

    async def execute(self, **kwargs) -> Any:
        url = kwargs.get("url")
        if not url:
            raise ValueError("URL is required")
        return f"Scraped content from {url}"
