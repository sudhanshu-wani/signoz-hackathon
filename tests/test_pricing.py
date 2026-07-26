import pytest

from shared.pricing import cost_usd, normalize_family


def test_normalize_family_matches_dated_ids():
    assert normalize_family("claude-haiku-4-5-20251001") == "haiku"
    assert normalize_family("claude-sonnet-4-6") == "sonnet"
    assert normalize_family("claude-opus-4-8") == "opus"


def test_unknown_model_falls_back_to_cheapest():
    # Fallback must not over-state cost.
    assert normalize_family("some-future-model") == "haiku"


def test_cost_is_input_plus_output():
    # 1M input @ $3 + 1M output @ $15 = $18 for sonnet
    assert cost_usd("claude-sonnet-4-6", 1_000_000, 1_000_000) == 18.0


def test_sonnet_costs_more_than_haiku_same_tokens():
    # The whole demo hinges on this gap existing.
    s = cost_usd("claude-sonnet-4-6", 10_000, 2_000)
    h = cost_usd("claude-haiku-4-5-20251001", 10_000, 2_000)
    assert s > h


def test_zero_tokens_is_zero_cost():
    assert cost_usd("claude-sonnet-4-6", 0, 0) == 0.0


def test_negative_tokens_raise():
    with pytest.raises(ValueError):
        cost_usd("claude-sonnet-4-6", -1, 0)
