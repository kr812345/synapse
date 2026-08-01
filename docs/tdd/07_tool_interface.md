# 7. Tool Interface and Registry

Agents in the AI OS are sandboxed. They do not have arbitrary code execution rights by default. If an agent wants to read a file, scrape a website, or post a tweet, it must request the capability via the **Tool Registry**.

## 7.1 Tool Definition
Every tool is defined by a strict schema. This is critical because the Model Router needs to translate these schemas into OpenAI/Anthropic/Gemini native tool-calling formats.

```python
class ToolInterface:
    name: str
    description: str
    parameters: dict # JSON Schema
    required_permissions: list[str]

    async def execute(self, **kwargs) -> any:
        pass
```

## 7.2 The Request Flow
1. Agent decides it needs to search the web.
2. Agent's prompt output includes a structured tool call block.
3. The Agent wrapper parses this and emits an event to the Tool Registry: `tool.execute(name="web_search", args={"query": "AI OS"})`.
4. Tool Registry checks the `AgentContract`. Does this agent have `"web_search"` in its `allowed_tools`?
5. If yes, the Tool Registry executes the code and returns the result to the Agent.
6. If no, the Tool Registry returns a `PermissionDenied` error, forcing the Agent to rethink its plan.

## 7.3 Human-in-the-Loop (HITL)
Dangerous tools (e.g., `git_commit`, `send_email`, `post_tweet`) require human approval.
When these tools are requested:
1. Execution pauses.
2. An event `tool.requires_approval` is broadcasted.
3. The Dashboard intercepts this and renders a UI prompt to the CEO (User).
4. Upon approval, an event is sent back to resume execution.

## 7.4 Standard Tools Library
The OS ships with a standard library of tools:
- **BrowserTool**: Headless scraping and DOM reading.
- **FilesystemTool**: Scoped read/write access to project directories.
- **GitTool**: Branching, committing, and PR creation.
- **PythonSandboxTool**: Secure execution of generated scripts.
- **SocialMediaTool**: API wrappers for Twitter/LinkedIn (requires HITL).
