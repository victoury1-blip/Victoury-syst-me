from dataclasses import dataclass
from typing import Optional


@dataclass
class Decision:
    action: str  # "increase" | "decrease" | "pause" | "hold" | "skip_cooldown" | "skip_low_data"
    new_budget: Optional[float] = None
    reason: str = ""


def extract_results(insights_row, purchase_action_types):
    if not insights_row:
        return 0.0
    # Meta's `actions` array reports the same purchase event under several
    # overlapping action_types at once (e.g. omni_purchase, purchase and
    # offsite_conversion.fb_pixel_purchase are usually all the same
    # conversions counted three different ways). Summing them triple-counts
    # a single sale, so take the first match in `purchase_action_types`
    # (a priority-ordered list), not a sum across all of them.
    values_by_type = {}
    for a in insights_row.get("actions", []) or []:
        values_by_type[a.get("action_type")] = float(a.get("value", 0))
    for action_type in purchase_action_types:
        if action_type in values_by_type:
            return values_by_type[action_type]
    return 0.0


def decide(insights_row, current_budget, days_since_last_change, config):
    spend = float(insights_row.get("spend", 0)) if insights_row else 0.0
    results = extract_results(insights_row, config["purchase_action_types"])

    if results < config["min_results_for_decision"]:
        return Decision(
            "skip_low_data",
            reason=f"{results:.0f} results in lookback window, need >= {config['min_results_for_decision']}",
        )

    cpa = spend / results if results else float("inf")
    target_cpa = config["target_cpa"]

    if days_since_last_change is not None and days_since_last_change < config["min_days_between_changes"]:
        return Decision(
            "skip_cooldown",
            reason=f"{days_since_last_change}d since last change, cooldown is {config['min_days_between_changes']}d (CPA {cpa:.2f})",
        )

    pause_threshold = target_cpa * config["pause_cpa_multiplier"]
    if cpa > pause_threshold:
        return Decision("pause", reason=f"CPA {cpa:.2f} > pause threshold {pause_threshold:.2f}")

    if cpa <= target_cpa:
        new_budget = min(current_budget * (1 + config["increase_pct"]), config["max_daily_budget"])
        if new_budget <= current_budget + 0.01:
            return Decision("hold", reason=f"CPA {cpa:.2f} <= target, but already at max_daily_budget")
        return Decision("increase", new_budget=round(new_budget, 2), reason=f"CPA {cpa:.2f} <= target {target_cpa:.2f}")

    new_budget = max(current_budget * (1 - config["decrease_pct"]), config["min_daily_budget"])
    if new_budget >= current_budget - 0.01:
        return Decision("hold", reason=f"CPA {cpa:.2f} > target, but already at min_daily_budget")
    return Decision("decrease", new_budget=round(new_budget, 2), reason=f"CPA {cpa:.2f} > target {target_cpa:.2f}")
