# 4. Agent Lifecycle and SDK

To ensure maximum code reuse and enforce strict contracts, every agent in the AI OS inherits from a base interface defined in the **Agent SDK**.

## 4.1 The Base Agent Interface

```typescript
// Conceptual TypeScript Interface (Implemented in Python via ABCs)
interface BaseAgent {
    // Identity Contract
    id: string;
    name: string;
    department: string;
    role: string;
    confidenceScore: number;

    // Permissions & Rules
    allowedTools(): string[];
    forbiddenActions(): string[];
    memoryAccessLevel(): string; // 'read-only', 'read-write', 'none'

    // Core Lifecycle Methods
    canHandle(task: TaskDescription): boolean;
    execute(task: Task): Promise<ExecutionResult>;
    validate(result: ExecutionResult): boolean;
    report(): Artifact;
    remember(knowledge: Knowledge): void;
}
```

## 4.2 The Lifecycle of an Agent's Task

When the Scheduler assigns a task to an Agent, the following strict lifecycle is enforced by the `BaseAgent` class wrappers:

### Step 1: Boot & Context Assembly (`prepare`)
- The agent wakes up.
- It queries the **Memory Engine** for context related to the task description.
- It loads its specific system prompt (Identity, Goal, Responsibilities, Forbidden Actions).

### Step 2: Execution Loop (`execute`)
- The agent formulates a plan.
- It requests tool execution via the **Tool Registry** (e.g., `search_web`, `read_github`).
- The Tool Registry verifies the agent's `allowedTools()` before executing.
- The agent synthesizes the results.

### Step 3: Self-Validation (`validate`)
- Before returning, the agent reviews its own output against the task requirements.
- If it fails validation, it loops back to Step 2 (up to a retry limit).

### Step 4: Knowledge Extraction (`remember`)
- The agent extracts atomic facts from its execution.
- It emits `memory.store_knowledge` events. Example: If it read a Reddit thread, it stores "Users are complaining about Feature X in Product Y" into the Knowledge Graph.

### Step 5: Artifact Generation (`report`)
- The agent does not simply return a JSON blob. It generates a permanent Markdown or Code artifact.
- The artifact is saved to disk, and the metadata is saved to the `artifacts` table.

### Step 6: Completion
- The agent emits a `task.completed` event containing the artifact ID and a brief summary.
- The agent goes dormant.

## 4.3 Why this matters
By standardizing this interface:
1. **Creating a new agent** requires only defining its prompt, allowed tools, and `canHandle` heuristics. The SDK handles the rest.
2. **Security**: An agent cannot bypass the Tool Registry to execute arbitrary code.
3. **Consistency**: Every task guarantees an artifact and knowledge extraction, preventing the "amnesia" common in standard AI agents.
