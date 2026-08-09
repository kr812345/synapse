# Handoff Report: Survey Explorer 1 — Model Router & Core Architecture

## Summary
Survey Explorer 1 has conducted a comprehensive, read-only analysis of the **Model Router** and **Core Architecture** in the Synapse codebase (`/root/synapse`). The investigation identified all core architectural boundaries, current mocked implementations in `models/model_router.py`, missing adapter structures specified in `docs/tdd/08_model_routing.md` and `docs/tdd/10_folder_structure.md`, and event-driven communication patterns across the kernel, scheduler, event bus, and shared models.

---

## 1. Observation

### 1.1 Core Architecture Components Observed
- **Kernel Interface & Implementation**:
  - `shared/interfaces.py`: Defines `Module(ABC)` (lines 4-14) and `KernelInterface(ABC)` (lines 16-23).
  - `kernel/kernel.py`: Defines `Kernel(KernelInterface)` (lines 8-29) which maintains `self.modules` and wires `self.event_bus`. Method `register_module` registers modules, subscribes them to `EventBus`, and injects kernel reference via `set_kernel`.
  - `events/event_bus.py`: `EventBus(Module)` (lines 10-44) handles event routing. Supports unicast messaging (`event.destination in subscribers`) and pub/sub broadcast (`event.destination == "*"`).
  - `shared/models.py`: Defines core Pydantic data schemas: `Event` (lines 6-12), `AgentContract` (lines 14-23), `Task` (lines 25-34), `DAG` (lines 36-42), and `Knowledge` (lines 45-54).

### 1.2 Model Router Current Implementation & Hardcoded Mocks
- File: `/root/synapse/models/model_router.py` (53 total lines)
- **Mocked Model Selection (`decide_model`)** (lines 18-26):
  ```python
  def decide_model(self, task_description: str) -> str:
      # Dummy logic to determine complexity
      words = len(task_description.split())
      if words < 10:
          return "Gemini Flash"
      elif words < 50:
          return "OpenRouter"
      else:
          return "Antigravity CLI"
  ```
  *Observation*: Uses naive word-count splitting (`len(task_description.split())`) with hardcoded limits (10, 50). Does not inspect prompt token count, requested tools, or agent confidence score as required by documentation.

- **Mocked Execution Output (`handle_event`)** (lines 28-52):
  ```python
  async def handle_event(self, event: Event) -> None:
      if event.event_type == "model.request_execution":
          task_id = event.payload.get("task_id")
          task_description = event.payload.get("task_description", "")
          agent = event.payload.get("agent", {})
          
          model = self.decide_model(task_description)
          logger.info(f"Model Router chose {model} for task {task_id}")
          
          # Simulate execution...
          result = {
              "status": "success",
              "executed_by": model,
              "agent": agent.get("identity"),
              "output": f"Simulated output from {model} for task {task_id}"
          }
          
          if self.kernel:
              resp = Event(
                  source=self.name,
                  destination=event.source,
                  event_type="model.execution_complete",
                  payload={"task_id": task_id, "result": result}
              )
              await self.kernel.send_event(resp)
  ```
  *Observation*: Contains hardcoded `# Simulate execution...` dictionary returning static string `"Simulated output from {model} for task {task_id}"`. No real LLM adapters, API connections, CLI execution calls, or fallback logic are present.

### 1.3 Missing Modules & Structure vs Architectural Specifications
- **Missing Adapters Directory & Classes**:
  - `docs/tdd/08_model_routing.md` Section 8.2 defines `ModelAdapter(ABC)` interface (`async def generate(prompt: str, tools: list) -> str`).
  - `docs/tdd/10_folder_structure.md` lines 31-37 envisions:
    - `models/adapters/gemini.py`
    - `models/adapters/openrouter.py`
    - `models/adapters/antigravity.py`
    - `models/cost_tracker.py`
  - *Observation*: Directory `/root/synapse/models/adapters` does NOT exist. Files `cost_tracker.py` and adapter python modules do NOT exist in `/root/synapse/models/`.

### 1.4 Test Suite & Inter-Module Interactions
- `tests/test_model_router.py`: Asserts that `model.request_execution` produces `model.execution_complete` with `"executed_by": "Gemini Flash"` (short prompt) and `"executed_by": "Antigravity CLI"` (long prompt).
- `scheduler/scheduler.py` (lines 108-114): Emits `model.request_execution` to `destination="model_router"` when an agent is found for a task. Expects `model.execution_complete` in return.
- `PYTHONPATH=. ./.venv/bin/pytest` execution result: 9 passed, 44 warnings in 2.20s.

---

## 2. Logic Chain

1. **Premise**: The user request and `ORIGINAL_REQUEST.md` (R1 & R2) require replacing mocked stubs in Model Router with production-ready functional code, adhering to `docs/architecture.md` and TDD specifications.
2. **Analysis of Current Code**:
   - `models/model_router.py` is the sole file handling LLM model selection and execution in the codebase.
   - Lines 18-26 split task descriptions by spaces and classify models as `"Gemini Flash"`, `"OpenRouter"`, or `"Antigravity CLI"`.
   - Lines 37-43 fabricate a mock string `"Simulated output from {model} for task {task_id}"`.
3. **Specification Comparison**:
   - `docs/tdd/08_model_routing.md` specifies a 3-tier routing strategy:
     - Tier 1 (Simple / High Volume): Gemini Flash (low complexity, summarization, JSON formatting).
     - Tier 2 (Medium / Standard): OpenRouter (Claude 3.5 Sonnet / Llama 3 70B, standard coding, marketing copy, DAG planning).
     - Tier 3 (Hard / Deep Reasoning): Antigravity CLI (Gemini 3.1 Pro / custom reasoning, system architecture, multi-file debugging).
   - TDD 8.1 specifies routing heuristics evaluating prompt/token complexity, requested tools count, and agent confidence score.
   - TDD 8.2 specifies a modular `ModelAdapter(ABC)` abstraction to isolate vendor-specific LLM implementations.
   - TDD 8.3 specifies fallback/redundancy handling so an OpenRouter or provider failure triggers transparent fallback to an alternative model adapter (e.g. Gemini Flash or Antigravity).
   - TDD 10 & TDD 02.6 specify cost tracking (`cost_tracker.py`), rate limits, and token usage reporting.
4. **Conclusion**: Production implementation of Model Router requires implementing the `ModelAdapter` abstract base class, developing adapter subclasses (`GeminiFlashAdapter`, `OpenRouterAdapter`, `AntigravityAdapter`), replacing `decide_model` with multi-tier heuristic logic, implementing retry/fallback mechanics in `ModelRouter.handle_event`, integrating token/cost tracking, and maintaining full event-compatibility with `scheduler.py` and `Kernel`.

---

## 3. Caveats

- **External API Keys & Environment**: The survey was strictly read-only and static. Actual API keys for OpenRouter or Gemini Flash may or may not be provided in the runtime environment. Adapters must gracefully handle offline/mock-fallback modes or API key presence checks so tests pass cleanly without network dependencies.
- **Other Departments**: Departments (Engineering, Research, Marketing, etc.) are handled by parallel survey explorers (Survey Explorer 2 & 3). Model Router interface design must remain generic to support calls originating from any department or scheduler.

---

## 4. Conclusion

`models/model_router.py` currently relies on hardcoded string output and simple word-length model selection. To make Model Router production-ready:
1. Abstract model generation behind a `ModelAdapter(ABC)` class in `models/adapters/base.py`.
2. Implement model adapters for Gemini Flash (`models/adapters/gemini.py`), OpenRouter (`models/adapters/openrouter.py`), and Antigravity CLI (`models/adapters/antigravity.py`).
3. Replace `decide_model` in `models/model_router.py` with multi-tier evaluation based on prompt complexity/tokens, tool complexity, and agent confidence score.
4. Implement automatic multi-tier fallback (e.g., primary adapter failure -> secondary tier adapter fallback).
5. Implement token and cost tracking module (`models/cost_tracker.py`).
6. Ensure `handle_event` formats the final output into `model.execution_complete` payload containing `result={"status": "success", "executed_by": model_name, "agent": agent_id, "output": output_text, "tokens": token_counts, "cost": estimated_cost}`.

---

## 5. Verification Method

To verify the Model Router and Core System Architecture:
1. **Inspect Code Files**:
   - `view_file` on `/root/synapse/models/model_router.py`
   - `view_file` on `/root/synapse/shared/interfaces.py`
   - `view_file` on `/root/synapse/shared/models.py`
   - `view_file` on `/root/synapse/kernel/kernel.py`
   - `view_file` on `/root/synapse/events/event_bus.py`
2. **Execute Pytest Suite**:
   - Run: `PYTHONPATH=. ./.venv/bin/pytest tests/test_model_router.py`
   - Run full suite: `PYTHONPATH=. ./.venv/bin/pytest`
3. **Invalidation Conditions**:
   - If tests fail, or `model.execution_complete` is not sent via Kernel `send_event`, or event envelope schema breaks compatibility with `scheduler.py`.

---

## Feature Inventory Additions

The following features and requirements were identified for the **Model Router** component:

| Feature ID | Feature Name | Description / Requirement Details | Source Specification |
|------------|--------------|----------------------------------|----------------------|
| **MR-01** | `ModelAdapter` Base Interface | Define abstract base class `ModelAdapter(ABC)` with `async generate(prompt: str, tools: list = None, **kwargs) -> str` to decouple provider implementations. | `docs/tdd/08_model_routing.md` Section 8.2 |
| **MR-02** | Gemini Flash Adapter | Implement Tier 1 adapter for fast, low-cost, high-volume tasks (JSON formatting, summarization, memory consolidation). | `docs/tdd/08_model_routing.md` Tier 1 & `docs/tdd/10_folder_structure.md` |
| **MR-03** | OpenRouter Adapter | Implement Tier 2 adapter for standard reasoning, coding, marketing copy, and DAG planning (Claude 3.5 Sonnet / Llama 3 70B). | `docs/tdd/08_model_routing.md` Tier 2 & `docs/tdd/10_folder_structure.md` |
| **MR-04** | Antigravity CLI Adapter | Implement Tier 3 adapter for deep reasoning, system architecture design, multi-file debugging, and security validation. | `docs/tdd/08_model_routing.md` Tier 3 & `docs/tdd/10_folder_structure.md` |
| **MR-05** | Multi-Tier Heuristic Model Selection | Enhance `decide_model` to evaluate prompt token count/length, requested tools, and `AgentContract.confidence_score` to route to Tiers 1, 2, or 3. | `docs/tdd/08_model_routing.md` Section 8.1 |
| **MR-06** | Fallback & Redundancy Mechanism | Implement automatic error catching and fallback execution when a primary provider fails (e.g. OpenRouter outage -> fallback to Gemini Flash or Antigravity). | `docs/tdd/08_model_routing.md` Section 8.3 |
| **MR-07** | Token Usage & Cost Tracking | Track input tokens, output tokens, and estimated financial cost per execution call, appending data to execution result payloads. | `docs/tdd/02_module_responsibilities.md` Section 2.6 & `docs/tdd/10_folder_structure.md` (`cost_tracker.py`) |
| **MR-08** | Real Execution Output Generation | Remove `"Simulated output from {model} for task {task_id}"` hardcoded mock strings in `models/model_router.py` and return actual adapter output. | `ORIGINAL_REQUEST.md` R1 & `models/model_router.py` |
| **MR-09** | Event Bus Compatibility | Maintain full compliance with `model.request_execution` and `model.execution_complete` event contracts on the Kernel Event Bus. | `docs/architecture.md` & `events/event_bus.py` |
