# Handoff Report: Model Router & Core Infrastructure (MR-01 to MR-09)

## 1. Observation
1. **Existing Code**: In `/root/synapse/models/model_router.py:20-43`:
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
   and simulated handle_event output:
   ```python
   result = {
       "status": "success",
       "executed_by": model,
       "agent": agent.get("identity"),
       "output": f"Simulated output from {model} for task {task_id}"
   }
   ```
2. **Missing Files**: `models/cost_tracker.py` and `models/adapters/` (`base.py`, `gemini.py`, `openrouter.py`, `antigravity.py`) do not exist yet on disk.
3. **Test Status**: Running `PYTHONPATH=. ./.venv/bin/pytest` on `/root/synapse` exits with code 0 (9 passed, 44 warnings). Existing test `tests/test_model_router.py` verifies basic routing strings `"Gemini Flash"` and `"Antigravity CLI"`.
4. **Event Bus Contracts**: In `scheduler/scheduler.py:108-133`, `Scheduler` emits `event_type="model.request_execution"` with payload `{"task_id": ..., "task_description": ..., "agent": ...}` and handles `event_type="model.execution_complete"` expecting `result` dictionary payload.

---

## 2. Logic Chain
1. **Observation 1 & 2** show that `ModelRouter` currently relies on hardcoded string returns without abstract provider interfaces, rate-limit fallback capabilities, or token/cost calculation modules.
2. Therefore, to satisfy features MR-01 to MR-09, we must create:
   - `models/adapters/base.py`: Abstract `ModelAdapter(ABC)` with `async generate(prompt: str, system: str | None = None, **kwargs) -> dict` interface and custom error hierarchy (`ModelAdapterError`, `RateLimitError`, `ProviderUnavailableError`, `AuthenticationError`).
   - `models/adapters/gemini.py`: Tier 1 `GeminiFlashAdapter` ($0.075/1M prompt, $0.30/1M completion) with live API / mock fallback.
   - `models/adapters/openrouter.py`: Tier 2 `OpenRouterAdapter` ($3.00/1M prompt, $15.00/1M completion) with live API / mock fallback.
   - `models/adapters/antigravity.py`: Tier 3 `AntigravityAdapter` ($5.00/1M prompt, $25.00/1M completion) with CLI process execution / mock fallback.
   - `models/cost_tracker.py`: `CostTracker` class to track token usage (prompt/completion tokens) and accumulate financial costs in USD per model tier and agent identity.
3. **Observation 1 & 4** show that `ModelRouter.decide_model` and `ModelRouter.handle_event` must be refactored:
   - `decide_model` will evaluate explicit hints (`payload.get("tier")`), keyword complexity rules, and prompt length thresholds to select the primary `ModelAdapter`.
   - `generate_with_fallback` will execute the primary adapter and automatically cascade to secondary adapters if errors occur.
   - `handle_event` will call `generate_with_fallback`, record metrics in `CostTracker`, format output adhering to `model.execution_complete` contract (`status`, `executed_by`, `agent`, `output`, `tokens`, `cost`), and emit back to requester.
4. **Observation 3** shows that backward compatibility with existing tests must be maintained so `pytest` continues passing with 100% success rate while testing real adapter output and cost metrics.

---

## 3. Caveats
- Actual live API key availability (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`) depends on environment execution context; adapters must handle unconfigured API keys by providing deterministic simulated fallback execution so pytest runs reliably in any offline CI/CD environment.
- Subprocess CLI execution for `AntigravityAdapter` must gracefully handle command absence or execution timeouts.

---

## 4. Conclusion
The Model Router design is fully specified across features MR-01 to MR-09. All adapter specifications, heuristic routing parameters, fallback mechanisms, cost tracking structures, event payload schemas, and test expectations are documented in detail in `analysis.md`. The implementation plan is clear, non-breaking, and ready for immediate coding by Implementer 1.

---

## 5. Verification Method
1. **Directory Verification**:
   Ensure `models/adapters/base.py`, `models/adapters/gemini.py`, `models/adapters/openrouter.py`, `models/adapters/antigravity.py`, and `models/cost_tracker.py` exist.
2. **Pytest Verification Command**:
   ```bash
   PYTHONPATH=. ./.venv/bin/pytest tests/test_model_router.py
   ```
3. **Full Suite Verification Command**:
   ```bash
   PYTHONPATH=. ./.venv/bin/pytest
   ```
   Must pass with 100% success rate.
