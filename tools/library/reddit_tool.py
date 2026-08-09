import os
from tools.tool_registry import ToolInterface

class RedditTool(ToolInterface):
    name = "reddit_api"
    description = "Searches Reddit for posts matching a query."
    parameters = {"query": "string", "subreddit": "string"}
    required_permissions = []

    async def execute(self, query: str = "", subreddit: str = "all", **kwargs) -> dict:
        import praw
        
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT", "SynapseOS/1.0")

        if not all([client_id, client_secret]):
            return {"status": "error", "message": "Reddit API credentials not configured in environment variables."}

        try:
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
            
            sub = reddit.subreddit(subreddit)
            results = []
            for post in sub.search(query, limit=5):
                results.append({
                    "title": post.title,
                    "score": post.score,
                    "url": post.url,
                    "subreddit": post.subreddit.display_name
                })
            return {"status": "success", "posts": results}
        except Exception as e:
            return {"status": "error", "message": str(e)}
