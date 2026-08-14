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

    campaign_name = os.environ.get("TARGET_CAMPAIGN_NAME", "SOLDE ENSEMBLE")
    ad_set_name = os.environ.get("NEW_AD_SET_NAME", "AD SET 2 - Ensemble Sport")
    daily_budget = float(os.environ.get("NEW_AD_SET_DAILY_BUDGET", "15"))
    currency = os.environ.get("CURRENCY", "USD")

    campaign = client.get_campaign_by_name(secrets["ad_account_id"], campaign_name)
    if not campaign:
        write_report([f"# Create Ad Set — failed", "", f"Campaign '{campaign_name}' not found in this account."])
        return

    pixels = client.list_pixels(secrets["ad_account_id"])
    pixel = next((p for p in pixels if p.get("name") == PIXEL_NAME), None)
    if not pixel:
        write_report([f"# Create Ad Set — failed", "", f"Pixel '{PIXEL_NAME}' not found on this ad account."])
        return

    # Same broad targeting as the campaign's proven ad set (Age 18-65, Morocco).
    # No publisher_platforms set on purpose: lets Meta use Advantage+ automatic
    # placements instead of a fixed, possibly overlapping placement list.
    targeting = {
        "age_min": 18,
        "age_max": 65,
        "geo_locations": {"countries": ["MA"]},
    }

    try:
        result = client.create_ad_set(
            secrets["ad_account_id"],
            campaign["id"],
            ad_set_name,
            to_minor_units(daily_budget, currency),
            targeting,
            pixel["id"],
        )
    except MetaGraphError as e:
        write_report([f"# Create Ad Set — failed", "", f"{e}"])
        return

    lines = [
        "# Ad Set Created",
        "",
        f"Campaign: **{campaign_name}** (`{campaign['id']}`)",
        f"New ad set: **{ad_set_name}** — ID `{result.get('id')}` — status **PAUSED**",
        f"Daily budget: {daily_budget:.2f} {currency}",
        "Targeting: Age 18-65, Morocco, Advantage+ automatic placements",
        "",
        "This ad set has no ad/creative yet — add your image/video and the ad copy to it in Ads Manager, then activate it manually when ready.",
    ]
    write_report(lines)
    send_telegram("\n".join(lines))


if __name__ == "__main__":
    main()
