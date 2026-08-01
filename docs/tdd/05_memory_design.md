# 5. Memory Design

The AI OS intentionally discards conversational memory (e.g., standard chat logs like `[{role: 'user', content: '...'}, {role: 'assistant', content: '...'}]`). Chat history is unstructured, prone to amnesia over long contexts, and impossible to query analytically.

Instead, the Memory Engine uses **Structured Atomic Knowledge**.

## 5.1 The Knowledge Object
Whenever an agent learns something, it distills it into a `Knowledge` object.

```json
{
  "id": "uuid-1234",
  "observation": "Competitor X is migrating from React to Svelte because of performance issues with their web dashboard.",
  "source": "Task_UUID / RedditAgent / r/webdev",
  "confidence": 0.85,
  "category": "competitor_tech_stack",
  "importance": 7,
  "embedding": [0.12, -0.45, ...],
  "expiration": null
}
```

## 5.2 Memory Buses and Retrieval
When an agent starts a task, it queries the Memory Engine. 
The Engine retrieves context using a hybrid approach:
1. **Semantic Search**: Vector similarity via `pgvector` on the `embedding` column against the task description.
2. **Metadata Filtering**: Hard filtering by `category`, minimum `importance`, or maximum `confidence`.
3. **Temporal Decay**: Filtering out rows where `expiration < NOW()`. (E.g., "Trending topics today" expires in 24 hours, whereas "CEO's name" never expires).

## 5.3 The Artifact Graph
Beyond atomic facts, the OS maintains an Artifact Graph.
Artifacts are long-form documents (e.g., a 10-page market research report). The Memory Engine embeds chunks of these artifacts.
If an agent asks "What did we conclude about Market X last month?", the Memory Engine can retrieve the exact Markdown artifact produced by the Research Department last month.

## 5.4 De-duplication and Consolidation
A background CRON task (implemented as an Agent) runs nightly:
1. It queries the Memory Engine for highly similar atomic facts.
2. It uses an LLM to consolidate them. (e.g., merging 5 tweets about a product launch into a single high-confidence observation).
3. It updates the database, keeping the knowledge base dense and relevant.
