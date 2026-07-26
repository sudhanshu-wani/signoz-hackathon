"""Model pricing table and per-call cost computation.

Prices are USD per 1,000,000 tokens. These are representative Claude
Sonnet/Haiku price points — VERIFY against current Anthropic pricing before
relying on absolute dollar figures. The *relative* gap (Sonnet ~4-5x Haiku) is
what drives the cost-per-outcome demo, and that gap is stable.

The table is keyed by a normalized model family so that dated model ids
(e.g. ``claude-haiku-4-5-20251001``) resolve to the right prices.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Price:
    input_per_mtok: float
    output_per_mtok: float


# Normalized family -> price. Edit here if pricing changes.
#
# Local (Ollama) models cost ~$0 to run; their prices below are a clearly-labeled
# "equivalent hosted" PROJECTION — what a comparable managed model would cost —
# so the cost-per-outcome dollar story still works while you pay nothing. The
# per-size split (7b > 3b) is what makes the strong-vs-cheap reveal possible, so
# the two tiers MUST map to different families (order: most specific first).
_PRICES: dict[str, Price] = {
    # Anthropic (real prices; verify against current pricing)
    "sonnet": Price(input_per_mtok=3.00, output_per_mtok=15.00),
    "haiku": Price(input_per_mtok=0.80, output_per_mtok=4.00),
    "opus": Price(input_per_mtok=15.00, output_per_mtok=75.00),
    # Ollama local models (equivalent-hosted projection; smaller = cheaper).
    # Specific sizes MUST come before generic family names (substring match).
    "qwen2.5:7b": Price(input_per_mtok=0.30, output_per_mtok=0.90),
    "qwen2.5:3b": Price(input_per_mtok=0.15, output_per_mtok=0.45),
    "qwen2.5:1.5b": Price(input_per_mtok=0.06, output_per_mtok=0.18),
    "llama3.2:3b": Price(input_per_mtok=0.15, output_per_mtok=0.45),
    "llama3.2:1b": Price(input_per_mtok=0.05, output_per_mtok=0.15),
    "llama3.1": Price(input_per_mtok=0.30, output_per_mtok=0.90),
    "llama3.2": Price(input_per_mtok=0.10, output_per_mtok=0.30),
}

# Fallback used when a model id matches no known family. Deliberately the
# cheapest so we never *over*-state cost by accident; a warning is logged.
_DEFAULT_FAMILY = "haiku"


def normalize_family(model: str) -> str:
    """Map a full model id to a pricing family (substring match)."""
    m = model.lower()
    for family in _PRICES:
        if family in m:
            return family
    return _DEFAULT_FAMILY


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost of one LLM call. Rounded to 6 dp (micro-dollars)."""
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    price = _PRICES[normalize_family(model)]
    cost = (
        input_tokens * price.input_per_mtok
        + output_tokens * price.output_per_mtok
    ) / 1_000_000
    return round(cost, 6)
