# 8. Model Routing Strategy

The AI OS treats Language Models as interchangeable compute engines, not as unique identities. The **Model Router** abstracts away API specifics and focuses on optimizing for Cost, Speed, and Reasoning Depth.

## 8.1 The Tiered Routing Logic

When an agent requests execution, the Model Router evaluates the task based on heuristics (token length, requested tools, agent confidence score) and routes the prompt accordingly.

### Tier 1: Simple / High-Volume (The Grunt Work)
- **Model**: Google Gemini Flash
- **Use Cases**: 
  - Summarizing long HTML scrapes.
  - Formatting JSON objects.
  - Consolidating basic memory atomic facts.
- **Why**: Blazing fast, extremely cheap, massive context window.

### Tier 2: Medium / Standard Logic (The Middle Management)
- **Model**: OpenRouter (Dynamic routing to Claude 3.5 Sonnet, Llama 3 70B, etc.)
- **Use Cases**:
  - Writing standard code modules.
  - Generating marketing copy.
  - Breaking down tasks into DAGs (Scheduler planning).
- **Why**: Excellent balance of high-quality reasoning and reasonable cost.

### Tier 3: Hard / Deep Reasoning (The Staff Engineer)
- **Model**: Antigravity CLI (Google Gemini 3.1 Pro / Custom reasoning architectures)
- **Use Cases**:
  - Designing complex system architectures.
  - Debugging multi-file dependency failures.
  - Validating critical security code.
- **Why**: Premium reasoning, slower execution, higher cost. Used sparingly and strictly controlled by the OS.

## 8.2 Model Adapter Interface
To ensure modularity, the Model Router does not hardcode API calls. It uses adapters.

```python
class ModelAdapter(ABC):
    @abstractmethod
    async def generate(self, prompt: str, tools: list) -> str:
        pass
```
If a new model drops tomorrow (e.g., GPT-5), we write a `GPT5Adapter` and register it with the Router. The rest of the OS, from the CEO down to the Reddit Agent, remains completely unchanged.

## 8.3 Fallback and Redundancy
If OpenRouter experiences an outage, the Model Router instantly falls back to Gemini Flash or Antigravity, ensuring the OS never experiences downtime due to a single vendor failure.
