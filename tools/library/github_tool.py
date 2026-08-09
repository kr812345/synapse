import os
from tools.tool_registry import ToolInterface

class GitHubTool(ToolInterface):
    name = "github_api"
    description = "Searches GitHub repositories based on a query string."
    parameters = {"query": "string"}
    required_permissions = []

    async def execute(self, query: str = "", **kwargs) -> dict:
        from github import Github
        
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            # Fallback to unauthenticated or just mock if no token for tests
            # Unauthenticated requests are heavily rate-limited
            g = Github()
        else:
            g = Github(token)
            
        try:
            # We search repositories for the query
            repos = g.search_repositories(query=query)
            results = []
            for repo in repos[:5]: # limit to 5
                results.append({
                    "name": repo.full_name,
                    "stars": repo.stargazers_count,
                    "description": repo.description,
                    "url": repo.html_url
                })
            return {"status": "success", "repos": results}
        except Exception as e:
            return {"status": "error", "message": str(e)}
