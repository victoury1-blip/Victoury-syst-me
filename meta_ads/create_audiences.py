from meta_ads.alerts import send_telegram, write_report
from meta_ads.config import load_secrets
from meta_ads.graph_api import MetaGraphClient, MetaGraphError

PIXEL_NAME = "victoury. maroc"

AUDIENCES_TO_CREATE = [
    {
        "name": "Website Visitors 180j (v2)",
        "event": "PageView",
        "exclude_event": None,
        "retention_days": 180,
    },
    {
        "name": "Purchasers 180j (v2)",
        "event": "Purchase",
        "exclude_event": None,
        "retention_days": 180,
    },
    {
        "name": "Retargeting - Visitors Non-Purchasers 30j (v2)",
        "event": "PageView",
        "exclude_event": "Purchase",
        "retention_days": 30,
    },
]


def main():
    secrets = load_secrets()
    client = MetaGraphClient(secrets["access_token"])

    pixels = client.list_pixels(secrets["ad_account_id"])
    pixel = next((p for p in pixels if p.get("name") == PIXEL_NAME), None)

    lines = ["# Custom Audiences — Creation Result", ""]

    if not pixel:
        lines.append(f"Pixel '{PIXEL_NAME}' not found on this ad account. No audiences were created.")
        write_report(lines)
        send_telegram("\n".join(lines))
        return

    lines.append(f"Pixel used: **{pixel['name']}** (`{pixel['id']}`)")
    lines.append("")

    for spec in AUDIENCES_TO_CREATE:
        try:
            result = client.create_website_custom_audience(
                secrets["ad_account_id"],
                spec["name"],
                pixel["id"],
                spec["event"],
                spec["retention_days"],
                exclude_event=spec["exclude_event"],
            )
            lines.append(f"- ✅ **{spec['name']}** created — ID `{result.get('id')}`")
        except MetaGraphError as e:
            lines.append(f"- ❌ **{spec['name']}** failed: {e}")

    lines.append("")
    lines.append(
        "Sizes take a few hours to a couple of days to populate as the pixel keeps firing. "
        "Re-run the Pixel Check workflow tomorrow to see them grow."
    )

    write_report(lines)
    send_telegram("\n".join(lines))


if __name__ == "__main__":
    main()
