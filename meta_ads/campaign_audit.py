from meta_ads.alerts import send_telegram, write_report
from meta_ads.audit import build_audit, format_audit
from meta_ads.config import load_config, load_secrets
from meta_ads.graph_api import MetaGraphClient


def main():
    config = load_config()
    secrets = load_secrets()
    client = MetaGraphClient(secrets["access_token"])
    currency = config.get("currency", "USD")
    lookback_days = config.get("report_lookback_days", "max")
    min_spend_for_history = config.get("audit_min_historical_spend", 20.0)

    audiences, campaign_details = build_audit(
        client,
        secrets["ad_account_id"],
        lookback_days,
        config["purchase_action_types"],
        min_spend_for_history,
    )
    lines = format_audit(audiences, campaign_details, currency)

    write_report(lines)
    send_telegram(
        "Meta Ads deep audit generated (audiences, targeting, creative, funnel) — "
        "see GitHub Actions summary for the full report."
    )


if __name__ == "__main__":
    main()
