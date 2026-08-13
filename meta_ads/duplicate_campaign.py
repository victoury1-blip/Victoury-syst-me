import os

from meta_ads.alerts import send_telegram, write_report
from meta_ads.config import load_secrets
from meta_ads.graph_api import MetaGraphClient, MetaGraphError


def main():
    secrets = load_secrets()
    client = MetaGraphClient(secrets["access_token"])

    source_name = os.environ.get("SOURCE_CAMPAIGN_NAME", "Retargeting")
    rename_suffix = os.environ.get("NEW_CAMPAIGN_SUFFIX", " - Relance")

    source = client.get_campaign_by_name(secrets["ad_account_id"], source_name)
    if not source:
        write_report([f"# Duplicate Campaign — failed", "", f"No campaign named '{source_name}' was found in this account."])
        return

    try:
        result = client.copy_campaign(source["id"], rename_suffix, deep_copy=True, status_option="PAUSED")
    except MetaGraphError as e:
        write_report([f"# Duplicate Campaign — failed", "", f"Could not duplicate '{source_name}' (`{source['id']}`): {e}"])
        return

    new_campaign_id = result.get("copied_campaign_id")
    account_number = secrets["ad_account_id"].replace("act_", "")
    lines = [
        "# Campaign Duplicated",
        "",
        f"Source: **{source_name}** (`{source['id']}`)",
        f"New campaign: `{new_campaign_id}` — created as **PAUSED** (nothing is live, no spend yet)",
        "",
        "Next: open Ads Manager, review/update the creative and audience on the new campaign, then activate it manually when ready:",
        f"https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={account_number}",
    ]
    write_report(lines)
    send_telegram("\n".join(lines))


if __name__ == "__main__":
    main()
