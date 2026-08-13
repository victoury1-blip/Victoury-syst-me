from meta_ads.alerts import send_telegram, write_report
from meta_ads.config import load_config, load_secrets
from meta_ads.graph_api import MetaGraphClient
from meta_ads.report import build_campaign_report, format_report


def main():
    config = load_config()
    secrets = load_secrets()
    client = MetaGraphClient(secrets["access_token"])
    currency = config.get("currency", "USD")
    lookback_days = config.get("report_lookback_days", 30)

    rows = build_campaign_report(client, secrets["ad_account_id"], lookback_days, config["purchase_action_types"])
    lines = format_report(rows, lookback_days, currency)

    write_report(lines)
    send_telegram("\n".join(lines))


if __name__ == "__main__":
    main()
