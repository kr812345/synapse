from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class CostTracker:
    """Tracks token consumption and USD financial cost across model router requests."""

    def __init__(self):
        self._records: List[Dict[str, Any]] = []

    def record_usage(
        self,
        task_id: Optional[str],
        agent: Optional[str],
        model_name: str,
        tier: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
    ) -> Dict[str, Any]:
        """Record a single LLM execution usage entry."""
        record = {
            "task_id": task_id or "unknown",
            "agent": agent or "unknown",
            "model_name": model_name,
            "tier": tier,
            "prompt_tokens": max(0, prompt_tokens),
            "completion_tokens": max(0, completion_tokens),
            "total_tokens": max(0, prompt_tokens + completion_tokens),
            "cost_usd": round(max(0.0, cost_usd), 6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._records.append(record)
        logger.debug(f"Recorded usage for task {task_id}: {cost_usd:.6f} USD, {record['total_tokens']} tokens")
        return record

    def get_summary(self) -> Dict[str, Any]:
        """Get overall aggregate metrics for all recorded executions."""
        total_prompt = sum(r["prompt_tokens"] for r in self._records)
        total_completion = sum(r["completion_tokens"] for r in self._records)
        total_cost = sum(r["cost_usd"] for r in self._records)

        return {
            "total_cost_usd": round(total_cost, 6),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "request_count": len(self._records),
        }

    def get_tier_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get aggregate metrics grouped by model tier (tier1, tier2, tier3)."""
        breakdown: Dict[str, Dict[str, Any]] = {}
        for r in self._records:
            tier = r["tier"]
            if tier not in breakdown:
                breakdown[tier] = {
                    "cost_usd": 0.0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "request_count": 0,
                }
            breakdown[tier]["cost_usd"] = round(breakdown[tier]["cost_usd"] + r["cost_usd"], 6)
            breakdown[tier]["prompt_tokens"] += r["prompt_tokens"]
            breakdown[tier]["completion_tokens"] += r["completion_tokens"]
            breakdown[tier]["total_tokens"] += r["total_tokens"]
            breakdown[tier]["request_count"] += 1

        return breakdown

    def get_agent_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get aggregate metrics grouped by requesting agent identity."""
        breakdown: Dict[str, Dict[str, Any]] = {}
        for r in self._records:
            agent = r["agent"]
            if agent not in breakdown:
                breakdown[agent] = {
                    "cost_usd": 0.0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "request_count": 0,
                }
            breakdown[agent]["cost_usd"] = round(breakdown[agent]["cost_usd"] + r["cost_usd"], 6)
            breakdown[agent]["prompt_tokens"] += r["prompt_tokens"]
            breakdown[agent]["completion_tokens"] += r["completion_tokens"]
            breakdown[agent]["total_tokens"] += r["total_tokens"]
            breakdown[agent]["request_count"] += 1

        return breakdown

    def reset(self) -> None:
        """Reset all recorded usage metrics."""
        self._records.clear()
