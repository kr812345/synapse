import requests
from bs4 import BeautifulSoup
from tools.tool_registry import ToolInterface

class BrowserTool(ToolInterface):
    name = "browser"
    description = "Fetches and extracts text from a given URL."
    parameters = {"url": "string"}
    required_permissions = ["network_access"]

    async def execute(self, url: str = "", **kwargs) -> dict:
        try:
            headers = {"User-Agent": "SynapseOS BrowserTool 1.0"}
            # We use a sync requests call here, but in production we'd use aiohttp
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract main text
            for script in soup(["script", "style"]):
                script.extract()
                
            text = soup.get_text(separator=' ')
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Limit the output to 2000 chars to avoid overwhelming the LLM
            return {"status": "success", "content": text[:2000]}
        except Exception as e:
            return {"status": "error", "message": str(e)}
