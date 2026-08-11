from datetime import date

from meta_ads.alerts import send_telegram, write_report
from meta_ads.config import load_config, load_secrets
from meta_ads.graph_api import MetaGraphClient, MetaGraphError
from meta_ads.rules import decide
from meta_ads.state import days_since, load_state, save_state

ZERO_DECIMAL_CURRENCIES = {"JPY", "KRW", "VND"}


def to_minor_units(amount, currency):
    if currency in ZERO_DECIMAL_CURRENCIES:
        return int(round(amount))
    return int(round(amount * 100))


def to_major_units(minor, currency):
    if currency in ZERO_DECIMAL_CURRENCIES:
        return float(minor)
    return minor / 100.0


def main():
    config = load_config()
    secrets = load_secrets()
    client = MetaGraphClient(secrets["access_token"])
    state = load_state()
    currency = config.get("currency", "USD")
    dry_run = config.get("dry_run", True)

    ad_set_ids = config.get("ad_set_ids") or []
    if ad_set_ids:
        ad_sets = [client.get_ad_set(a) for a in ad_set_ids]
    else:
        ad_sets = client.list_active_ad_sets(secrets["ad_account_id"], config.get("campaign_ids") or None)

    lines = [f"# Meta Ads Daily Budget Report — {date.today().isoformat()}", ""]
    if dry_run:
        lines.append("_Mode: DRY RUN — no changes were applied to Meta_")
        lines.append("")

    for ad_set in ad_sets:
        ad_set_id = ad_set["id"]
        name = ad_set.get("name", ad_set_id)
        current_budget = to_major_units(int(ad_set.get("daily_budget", 0)), currency)

        try:
            insights = client.get_insights(ad_set_id, config["lookback_days"])
        except MetaGraphError as e:
            lines.append(f"- **{name}**: failed to fetch insights ({e})")
            continue

        ad_state = state.get(ad_set_id, {})
        d_since = days_since(ad_state.get("last_change_date"))
        decision = decide(insights, current_budget, d_since, config)

        line = f"- **{name}** (budget {current_budget:.2f} {currency}): {decision.action} — {decision.reason}"

        try:
            if decision.action in ("increase", "decrease"):
                if not dry_run:
                    client.update_daily_budget(ad_set_id, to_minor_units(decision.new_budget, currency))
                    state[ad_set_id] = {
                        **ad_state,
                        "last_change_date": date.today().isoformat(),
                        "last_budget": decision.new_budget,
                    }
                    line += f" -> new budget {decision.new_budget:.2f} {currency}"
                else:
                    line += f" -> would set budget to {decision.new_budget:.2f} {currency} (dry run)"
            elif decision.action == "pause":
                if not dry_run:
                    client.pause_ad_set(ad_set_id)
                    state[ad_set_id] = {**ad_state, "paused_date": date.today().isoformat()}
                    line += " -> PAUSED"
                else:
                    line += " -> would PAUSE (dry run)"
        except MetaGraphError as e:
            line += f" | FAILED to apply change: {e}"

        lines.append(line)

    save_state(state)
    write_report(lines)
    send_telegram("\n".join(lines))


if __name__ == "__main__":
    main()
