from typing import Dict, Optional
from pydantic import BaseModel


class ModelPricing(BaseModel):
    prompt_cost_per_1k: float  # USD per 1,000 prompt tokens
    completion_cost_per_1k: float  # USD per 1,000 completion tokens


# Default pricing registry (configurable at runtime without hardcoding permanently)
DEFAULT_PRICING: Dict[str, ModelPricing] = {
    "gpt-4o": ModelPricing(prompt_cost_per_1k=0.005, completion_cost_per_1k=0.015),
    "gpt-4o-mini": ModelPricing(prompt_cost_per_1k=0.00015, completion_cost_per_1k=0.0006),
    "gpt-3.5-turbo": ModelPricing(prompt_cost_per_1k=0.0005, completion_cost_per_1k=0.0015),
    "claude-3-5-sonnet": ModelPricing(prompt_cost_per_1k=0.003, completion_cost_per_1k=0.015),
    "gemini-1.5-pro": ModelPricing(prompt_cost_per_1k=0.0035, completion_cost_per_1k=0.0105),
    "gemini-1.5-flash": ModelPricing(prompt_cost_per_1k=0.000075, completion_cost_per_1k=0.0003),
    "gemini-2.5-flash": ModelPricing(prompt_cost_per_1k=0.000075, completion_cost_per_1k=0.0003),
    "mock-llm": ModelPricing(prompt_cost_per_1k=0.0001, completion_cost_per_1k=0.0002),
    "default": ModelPricing(prompt_cost_per_1k=0.001, completion_cost_per_1k=0.002),
}


class CostTracker:
    """Calculates and aggregates token consumption and financial cost for LLM calls."""

    def __init__(self, pricing_table: Optional[Dict[str, ModelPricing]] = None):
        self._pricing: Dict[str, ModelPricing] = pricing_table or dict(DEFAULT_PRICING)

    def set_pricing(self, model: str, prompt_cost_per_1k: float, completion_cost_per_1k: float) -> None:
        """Dynamically update pricing for a given model."""
        self._pricing[model.lower()] = ModelPricing(
            prompt_cost_per_1k=prompt_cost_per_1k,
            completion_cost_per_1k=completion_cost_per_1k,
        )

    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate estimated cost in USD."""
        pricing = self._pricing.get(model.lower(), self._pricing.get("default", DEFAULT_PRICING["default"]))
        prompt_cost = (prompt_tokens / 1000.0) * pricing.prompt_cost_per_1k
        completion_cost = (completion_tokens / 1000.0) * pricing.completion_cost_per_1k
        return round(prompt_cost + completion_cost, 6)


# Global singleton instance
cost_tracker = CostTracker()
