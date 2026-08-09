# Model Router Architecture & Requirements Analysis (MR-01 to MR-09)

## Executive Summary
This report presents a thorough investigation of the Model Router system in Synapse AI OS. Currently, `models/model_router.py` contains a minimal stub with hardcoded mock response strings (`"Simulated output from {model} for task {task_id}"`) and naive word-count based model selection. There are no provider adapters or cost tracking modules currently implemented in `models/`. 

To fulfill features MR-01 through MR-09 for Milestone 1, we define a modular, multi-tier architecture powered by abstract model adapters, multi-tier heuristic routing, fallback redundancy, token usage and USD cost tracking, and strict adherence to the Event Bus contract (`model.request_execution` -> `model.execution_complete`).

---

## 1. Existing Codebase Audit

### 1.1 `models/model_router.py`
- **Location**: `/root/synapse/models/model_router.py` (53 lines)
- **Current Behavior**:
  - `decide_model(task_description)`: Simple string word count split. Returns string `"Gemini Flash"` if < 10 words, `"OpenRouter"` if < 50 words, `"Antigravity CLI"` otherwise.
  - `handle_event(event)`: Listens for `event.event_type == "model.request_execution"`. Constructs a static mock dictionary:
    ```python
    result = {
        "status": "success",
        "executed_by": model,
        "agent": agent.get("identity"),
        "output": f"Simulated output from {model} for task {task_id}"
    }
    ```
  - Emits `model.execution_complete` back to `event.source`.
- **Deficiencies**:
  - No actual LLM provider integration.
  - No adapter interface abstraction.
  - No retry or fallback logic if a provider fails or rate-limits.
  - No token counter or USD cost tracker (`cost_tracker.py` missing).
  - No handling of explicit model/tier hints or task complexity categories.

### 1.2 `tests/test_model_router.py`
- **Location**: `/root/synapse/tests/test_model_router.py` (62 lines)
- **Current Behavior**:
  - Tests basic async dispatch via `Kernel` and `MockScheduler`.
  - Asserts `resp1.payload["result"]["executed_by"] == "Gemini Flash"` for short description.
  - Asserts `resp2.payload["result"]["executed_by"] == "Antigravity CLI"` for long description.
- **Contract Requirement**:
  - `executed_by` in the result payload must maintain compatible display names (`"Gemini Flash"`, `"OpenRouter"`, `"Antigravity CLI"`) or detailed model strings while satisfying `executed_by` expectations.

### 1.3 `scheduler/scheduler.py` Event Bus Interaction
- **Location**: `/root/synapse/scheduler/scheduler.py:108-133`
- **Current Behavior**:
  - Emits `model.request_execution` with payload `{"task_id": task.id, "task_description": task.description, "agent": contract_data}`.
  - Expects `model.execution_complete` back with payload `{"task_id": task_id, "result": result}`.
  - Expects `result` dictionary containing execution output, agent metadata, status, etc.

---

## 2. Feature Specifications (MR-01 to MR-09)

### Feature MR-01: Abstract `ModelAdapter(ABC)`
- **Target File**: `models/adapters/base.py`
- **Description**: Abstract base class defining the provider interface and exceptions.
- **Exceptions**:
  - `ModelAdapterError(Exception)`: Base exception for model generation failures.
  - `RateLimitError(ModelAdapterError)`: HTTP 429 / rate quota exceeded.
  - `ProviderUnavailableError(ModelAdapterError)`: HTTP 5xx / API connectivity failures.
  - `AuthenticationError(ModelAdapterError)`: Invalid or missing API key.
- **Interface Contract**:
  ```python
  class ModelAdapter(ABC):
      @property
      @abstractmethod
      def name(self) -> str:
          """Display name (e.g. 'Gemini Flash', 'OpenRouter', 'Antigravity CLI')."""
          pass

      @property
      @abstractmethod
      def model_id(self) -> str:
          """Provider model identifier (e.g. 'gemini-2.5-flash', 'openrouter/auto', 'antigravity-cli')."""
          pass

      @property
      @abstractmethod
      def tier(self) -> str:
          """Tier label ('tier1', 'tier2', 'tier3')."""
          pass

      @property
      @abstractmethod
      def cost_per_1k_prompt(self) -> float:
          """Cost in USD per 1,000 prompt tokens."""
          pass

      @property
      @abstractmethod
      def cost_per_1k_completion(self) -> float:
          """Cost in USD per 1,000 completion tokens."""
          pass

      @abstractmethod
      async def generate(self, prompt: str, system: str | None = None, **kwargs) -> dict:
          """Generate response text from LLM provider.
          
          Returns dict matching standard schema:
          {
              "output": str,
              "model_name": str,
              "tier": str,
              "prompt_tokens": int,
              "completion_tokens": int,
              "total_tokens": int,
              "cost_usd": float,
              "raw_response": dict | None
          }
          """
          pass
  ```

---

### Feature MR-02: `GeminiFlashAdapter` (Tier 1)
- **Target File**: `models/adapters/gemini.py`
- **Class**: `GeminiFlashAdapter(ModelAdapter)`
- **Tier**: Tier 1 (Low complexity, high volume, low latency, low cost)
- **Model ID**: `gemini-2.5-flash`
- **Pricing**: Prompt = $0.000075 / 1k tokens ($0.075 / 1M), Completion = $0.000300 / 1k tokens ($0.30 / 1M)
- **Behavior**:
  - Inspects `GEMINI_API_KEY` from `os.environ`.
  - If API key is present, calls Gemini REST API / SDK (`google.genai` / `httpx`).
  - If API key is absent or in fallback mode (e.g., unit testing environment), executes local deterministic simulation engine that computes actual character token approximations (`len(prompt) // 4`, `len(output) // 4`) and calculates USD cost.

---

### Feature MR-03: `OpenRouterAdapter` (Tier 2)
- **Target File**: `models/adapters/openrouter.py`
- **Class**: `OpenRouterAdapter(ModelAdapter)`
- **Tier**: Tier 2 (Standard reasoning, general coding, departmental worker tasks)
- **Model ID**: `openrouter/auto` (or `anthropic/claude-3.5-sonnet`)
- **Pricing**: Prompt = $0.0030 / 1k tokens ($3.00 / 1M), Completion = $0.0150 / 1k tokens ($15.00 / 1M)
- **Behavior**:
  - Inspects `OPENROUTER_API_KEY` from `os.environ`.
  - Uses OpenAI-compatible HTTP POST to `https://openrouter.ai/api/v1/chat/completions`.
  - Graceful fallback execution when API key is missing or offline mode active.

---

### Feature MR-04: `AntigravityAdapter` (Tier 3)
- **Target File**: `models/adapters/antigravity.py`
- **Class**: `AntigravityAdapter(ModelAdapter)`
- **Tier**: Tier 3 (Deep reasoning, complex architecture, multi-step problem solving)
- **Model ID**: `antigravity-cli`
- **Pricing**: Prompt = $0.0050 / 1k tokens ($5.00 / 1M), Completion = $0.0250 / 1k tokens ($25.00 / 1M)
- **Behavior**:
  - Invokes CLI tool (e.g. `agy` via `asyncio.create_subprocess_exec`) or API bridge.
  - Handles subprocess execution timeouts and fallback simulation.

---

### Feature MR-05: Multi-tier Heuristic Router (`decide_model`)
- **Target File**: `models/model_router.py`
- **Signature**: `decide_model(self, task_description: str, payload: dict | None = None) -> ModelAdapter`
- **Multi-Factor Heuristics**:
  1. **Explicit Hint**:
     - Check `payload.get("tier")` or `payload.get("model_hint")`. If `"tier1"` or `"gemini"`, select `GeminiFlashAdapter`. If `"tier2"` or `"openrouter"`, select `OpenRouterAdapter`. If `"tier3"` or `"antigravity"`, select `AntigravityAdapter`.
  2. **Keyword Complexity Scoring**:
     - **Tier 3 (Deep Reasoning)**: `"architecture"`, `"design"`, `"refactor"`, `"security audit"`, `"optimization"`, `"deep research"`, `"root cause"`, `"complex task"`
     - **Tier 2 (Standard Reasoning)**: `"code"`, `"feature"`, `"implement"`, `"unit test"`, `"data model"`, `"department"`, `"search"`
     - **Tier 1 (Simple/High-Volume)**: `"summary"`, `"format"`, `"ping"`, `"echo"`, `"log"`, `"simple"`, `"classify"`
  3. **Prompt Length / Token Thresholds**:
     - Words < 10 or Chars < 80 -> Tier 1 (`GeminiFlashAdapter`)
     - Words 10 to 50 or Chars 80 to 400 -> Tier 2 (`OpenRouterAdapter`)
     - Words > 50 or Chars > 400 -> Tier 3 (`AntigravityAdapter`)

---

### Feature MR-06: Automatic Fallback / Redundancy Logic
- **Target File**: `models/model_router.py`
- **Method**: `async generate_with_fallback(self, prompt: str, system: str | None = None, preferred_tier: str | None = None, **kwargs) -> dict`
- **Execution Chain**:
  - Preferred adapter is attempted first.
  - If preferred adapter raises `ModelAdapterError`, `RateLimitError`, `ProviderUnavailableError`, `TimeoutError`, or `Exception`:
    - Log `logger.warning("Adapter %s failed with %s. Attempting fallback...", adapter.name, exc)`
    - Step to next adapter in ordered fallback list (e.g. Tier 1 -> Tier 2 -> Tier 3; Tier 2 -> Tier 3 -> Tier 1; Tier 3 -> Tier 2 -> Tier 1).
  - If all adapters fail:
    - Log `logger.error("All model adapters failed.")`
    - Raise `RuntimeError("All model adapters failed to execute prompt")` or return failure payload.

---

### Feature MR-07: `CostTracker` Module
- **Target File**: `models/cost_tracker.py`
- **Class**: `CostTracker`
- **Responsibilities**:
  - Records usage events containing `task_id`, `agent`, `model_name`, `tier`, `prompt_tokens`, `completion_tokens`, `cost_usd`, and `timestamp`.
  - Aggregates global totals (`total_cost_usd`, `total_prompt_tokens`, `total_completion_tokens`, `total_tokens`).
  - Provides breakdown queries:
    - `get_summary() -> dict`
    - `get_tier_breakdown() -> dict`
    - `get_agent_breakdown() -> dict`
    - `reset() -> None` (for test suite cleanup)

---

### Feature MR-08 & MR-09: Real Execution Outputs & Event Bus Contract Compliance
- **Target File**: `models/model_router.py`
- **Event Bus Input**: `event_type == "model.request_execution"`
  - Payload parameters: `task_id`, `task_description`, `agent`, `system`, `tier`, `tools`
- **Execution Workflow**:
  1. Call `decide_model(task_description, event.payload)` to obtain primary adapter.
  2. Call `generate_with_fallback(task_description, system=system, preferred_adapter=primary)` to obtain execution result.
  3. Record token usage and USD cost in `CostTracker`.
  4. Construct `result` dict:
     ```python
     result = {
         "status": "success",
         "executed_by": adapter_result["model_name"], # e.g. "Gemini Flash" / "OpenRouter" / "Antigravity CLI"
         "agent": agent.get("identity") if agent else "unknown",
         "output": adapter_result["output"],
         "tokens": {
             "prompt_tokens": adapter_result["prompt_tokens"],
             "completion_tokens": adapter_result["completion_tokens"],
             "total_tokens": adapter_result["total_tokens"]
         },
         "cost": adapter_result["cost_usd"]
     }
     ```
  5. Construct response `Event`:
     - `source`: `"model_router"`
     - `destination`: `event.source`
     - `event_type`: `"model.execution_complete"`
     - `payload`: `{"task_id": task_id, "result": result}`
  6. Call `await self.kernel.send_event(resp)`

---

## 3. Directory Layout & File Structure

```
models/
├── __init__.py
├── model_router.py          # Refactored ModelRouter module with heuristic routing & fallback
├── cost_tracker.py          # CostTracker class for token usage and financial cost tracking
└── adapters/
    ├── __init__.py
    ├── base.py              # Abstract ModelAdapter(ABC) and exception classes
    ├── gemini.py            # Tier 1 GeminiFlashAdapter
    ├── openrouter.py        # Tier 2 OpenRouterAdapter
    └── antigravity.py       # Tier 3 AntigravityAdapter
```

---

## 4. Test Strategy (`tests/test_model_router.py`)

1. **Adapter Unit Tests**:
   - Verify `generate()` output schema for GeminiFlashAdapter, OpenRouterAdapter, AntigravityAdapter.
   - Verify token count calculation and USD cost calculation.
2. **CostTracker Unit Tests**:
   - Verify usage recording, total cost accumulation, and tier/agent breakdown.
3. **Multi-tier Heuristic Router Tests**:
   - Verify word count limits (short -> Gemini Flash, medium -> OpenRouter, long -> Antigravity CLI).
   - Verify explicit model hints (`payload={"tier": "tier2"}`).
   - Verify keyword complexity rules.
4. **Fallback Mechanism Tests**:
   - Mock primary adapter failure (e.g. `RateLimitError`) and verify automatic fallback to secondary adapter.
5. **Event Bus Integration Tests**:
   - Execute full end-to-end event dispatch via `Kernel` and `MockScheduler`.
   - Verify `model.request_execution` receives `model.execution_complete` response with real token metadata and USD cost.
