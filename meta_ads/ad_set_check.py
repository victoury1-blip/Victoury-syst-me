import os

from meta_ads.alerts import send_telegram, write_report
from meta_ads.config import load_config, load_secrets
from meta_ads.graph_api import MetaGraphClient, MetaGraphError
from meta_ads.rules import extract_results

ZERO_DECIMAL_CURRENCIES = {"JPY", "KRW", "VND"}


def to_major_units(minor, currency):
    if currency in ZERO_DECIMAL_CURRENCIES:
        return float(minor)
    return minor / 100.0


def main():
    config = load_config()
    secrets = load_secrets()
    client = MetaGraphClient(secrets["access_token"])
    currency = config.get("currency", "USD")

    campaign_name = os.environ.get("CAMPAIGN_NAME", "SOLDE ENSEMBLE")
    ad_set_name = os.environ.get("AD_SET_NAME", "AD SET 1 SOLDE")
    lookback_days = os.environ.get("LOOKBACK_DAYS", "4")
    if lookback_days not in ("max", "maximum", "today"):
        lookback_days = int(lookback_days)

    campaign = client.get_campaign_by_name(secrets["ad_account_id"], campaign_name)
    if not campaign:
        write_report([f"# Ad Set Check — failed", "", f"Campaign '{campaign_name}' not found."])
        return

    ad_set = next(
        (a for a in client.list_ad_sets_for_campaign(campaign["id"]) if a.get("name") == ad_set_name),
        None,
    )
    if not ad_set:
        write_report([f"# Ad Set Check — failed", "", f"Ad set '{ad_set_name}' not found in '{campaign_name}'."])
        return

    try:
        insights = client.get_insights_full(ad_set["id"], lookback_days)
    except MetaGraphError as e:
        write_report([f"# Ad Set Check — failed", "", f"{e}"])
        return

    spend = float(insights.get("spend", 0)) if insights else 0.0
    results = extract_results(insights, config["purchase_action_types"])
    cpa = spend / results if results else None
    current_budget = to_major_units(int(ad_set.get("daily_budget", 0)), currency)
    period = f"last {lookback_days} days" if isinstance(lookback_days, int) else lookback_days

    lines = [
        f"# Ad Set Check — {ad_set_name} ({period})",
        "",
        f"Campaign: **{campaign_name}**",
        f"Current daily budget: {current_budget:.2f} {currency}",
        f"Spend: {spend:.2f} {currency}",
        f"Results: {results:.0f}",
        f"CPA: {cpa:.2f} {currency}" if cpa is not None else "CPA: - (no results)",
    ]
    write_report(lines)
    send_telegram("\n".join(lines))


if __name__ == "__main__":
    main()
