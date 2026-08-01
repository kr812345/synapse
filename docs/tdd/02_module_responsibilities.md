# 2. Module Responsibilities

Every component in the AI OS is an isolated module that implements the `BaseModule` interface. This ensures strict boundaries and high cohesion.

## 2.1 AI OS Kernel
The heart of the operating system.
- **Responsibility**: Maintains the module registry and provides the core API boundary.
- **Behavior**: It does not perform logic. It simply wires the system together. When a module boots, it registers with the Kernel. The Kernel injects the Event Bus into the module.
- **State**: Holds references to all active modules.

## 2.2 Event Bus
The nervous system of the OS.
- **Responsibility**: Routes `Event` objects between modules.
- **Behavior**: Supports direct messaging (`destination="research_manager"`) and pub/sub broadcasting (`destination="*"`).
- **State**: Maintains subscriber lists and topic mappings.

## 2.3 Task Scheduler (DAG Orchestrator)
The executive function of the OS.
- **Responsibility**: Manages the lifecycle of tasks and Task Graphs.
- **Behavior**: 
  1. Receives a complex task.
  2. Breaks it down into a DAG (often by querying a planning model).
  3. Finds the appropriate department/agent via the Agent Registry.
  4. Dispatches the task and waits for completion events.
  5. Unblocks dependent tasks in the DAG.
- **State**: The current queue, active DAGs, and task statuses (`pending`, `executing`, `validating`, `completed`, `failed`).

## 2.4 Agent Registry
The HR department of the OS.
- **Responsibility**: Maintains the contracts and capabilities of all available agents.
- **Behavior**: Answers queries from the Scheduler like "Who can handle a task requiring 'python' and 'database' skills?"
- **State**: A directory of `AgentContract` objects representing every live worker.

## 2.5 Memory Engine
The long-term brain.
- **Responsibility**: Stores and retrieves structured knowledge, observations, and artifact references.
- **Behavior**: Receives raw observations, generates vector embeddings, stores them in PostgreSQL (pgvector), and retrieves them based on semantic similarity or temporal queries.
- **State**: Ephemeral cache of recent memory; persistent state lives in the database.

## 2.6 Model Router
The financial and computational optimizer.
- **Responsibility**: Executes prompts against LLMs.
- **Behavior**: Intercepts `model.request_execution` events. Analyzes the payload's complexity and token count.
  - **Low Complexity / High Volume**: Routes to Gemini Flash (Fast, Cheap).
  - **Medium Complexity**: Routes to OpenRouter models (e.g., Claude 3.5 Sonnet, Llama 3).
  - **High Complexity / Deep Reasoning**: Routes to Antigravity CLI / Gemini 3.1 Pro.
- **State**: API keys, rate limits, and cost tracking.

## 2.7 Tool Registry
The equipment room.
- **Responsibility**: Provides sandboxed access to external capabilities (Filesystem, Shell, GitHub API, Twitter API).
- **Behavior**: Agents request tool execution. The registry validates the agent's permissions (from their `AgentContract`), executes the tool, and returns the result.
- **State**: Tool schemas, active connections, and execution sandboxes.

## 2.8 The Dashboard (Phase 4)
The CEO's monitor.
- **Responsibility**: Provides a live, visual interface into the OS's operations.
- **Behavior**: Subscribes to all events via the Event Bus (Read-Only). Renders active DAGs, agent states, live logs, memory graphs, and running costs.
- **State**: Web UI state (React/Next.js).
