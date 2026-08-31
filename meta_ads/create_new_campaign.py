import os

from meta_ads.alerts import send_telegram, write_report
from meta_ads.config import load_secrets
from meta_ads.graph_api import MetaGraphClient, MetaGraphError

PIXEL_NAME = "victoury. maroc"

ZERO_DECIMAL_CURRENCIES = {"JPY", "KRW", "VND"}


def to_minor_units(amount, currency):
    if currency in ZERO_DECIMAL_CURRENCIES:
        return int(round(amount))
    return int(round(amount * 100))


def main():
    secrets = load_secrets()
    client = MetaGraphClient(secrets["access_token"])

    campaign_name = os.environ.get("NEW_CAMPAIGN_NAME", "Nouvelle Campagne V2")
    ad_set_name = os.environ.get("NEW_AD_SET_NAME", "AD SET 1")
    daily_budget = float(os.environ.get("NEW_AD_SET_DAILY_BUDGET", "15"))
    currency = os.environ.get("CURRENCY", "USD")

    pixels = client.list_pixels(secrets["ad_account_id"])
    pixel = next((p for p in pixels if p.get("name") == PIXEL_NAME), None)
    if not pixel:
        write_report([f"# Create Campaign — failed", "", f"Pixel '{PIXEL_NAME}' not found on this ad account."])
        return

    try:
        campaign = client.create_campaign(secrets["ad_account_id"], campaign_name)
    except MetaGraphError as e:
        write_report([f"# Create Campaign — failed", "", f"{e}"])
        return

    # Same broad targeting as the account's proven ad sets (Age 18-65,
    # Morocco). No publisher_platforms: lets Meta use Advantage+ automatic
    # placements instead of a fixed, possibly overlapping placement list.
    targeting = {
        "age_min": 18,
        "age_max": 65,
        "geo_locations": {"countries": ["MA"]},
    }

    try:
        ad_set = client.create_ad_set(
            secrets["ad_account_id"],
            campaign["id"],
            ad_set_name,
            to_minor_units(daily_budget, currency),
            targeting,
            pixel["id"],
        )
    except MetaGraphError as e:
        lines = [
            "# Campaign Created (ad set failed)",
            "",
            f"Campaign: **{campaign_name}** — ID `{campaign['id']}` — status **PAUSED**",
            f"Ad set creation failed: {e}",
            "You can add an ad set manually in Ads Manager for this campaign.",
        ]
        write_report(lines)
        send_telegram("\n".join(lines))
        return

    lines = [
        "# Campaign + Ad Set Created",
        "",
        f"Campaign: **{campaign_name}** — ID `{campaign['id']}` — status **PAUSED**",
        f"Ad set: **{ad_set_name}** — ID `{ad_set.get('id')}` — status **PAUSED**",
        f"Daily budget: {daily_budget:.2f} {currency}",
        "Targeting: Age 18-65, Morocco, Advantage+ automatic placements",
        "",
        "Nothing has an ad/creative yet — add your 2 creatives as ads inside this ad set in Ads Manager, then activate the campaign and ad set manually when ready.",
    ]
    write_report(lines)
    send_telegram("\n".join(lines))


if __name__ == "__main__":
    main()
