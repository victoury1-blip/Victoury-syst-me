import json
from datetime import datetime, timezone

from meta_ads.alerts import send_telegram, write_report
from meta_ads.config import load_secrets
from meta_ads.graph_api import MetaGraphClient


def days_since(iso_timestamp):
    if not iso_timestamp:
        return None
    try:
        fired = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - fired).days


def main():
    secrets = load_secrets()
    client = MetaGraphClient(secrets["access_token"])

    pixels = client.list_pixels(secrets["ad_account_id"])
    audiences = client.list_custom_audiences(secrets["ad_account_id"])

    lines = ["# Pixel & Audience Check", ""]

    lines += ["## Pixels linked to this ad account", "", "| Name | ID | Last fired | Days ago | Created |", "|---|---|---|---|---|"]
    for p in pixels:
        last_fired = p.get("last_fired_time")
        d = days_since(last_fired)
        status = f"{d}d ago" if d is not None else "never / unknown"
        lines.append(f"| {p.get('name', '-')} | `{p.get('id')}` | {last_fired or '-'} | {status} | {p.get('creation_time', '-')} |")
    lines.append("")

    lines += ["## Custom Audiences — raw data source (to see which pixel each one is built from)", "", "| Name | Approx. size | Raw data_source |", "|---|---|---|"]
    for a in audiences:
        lo = a.get("approximate_count_lower_bound")
        hi = a.get("approximate_count_upper_bound")
        size = f"{lo}-{hi}" if lo is not None else "-"
        source_raw = json.dumps(a.get("data_source") or {}, ensure_ascii=False)
        lines.append(f"| {a.get('name', '-')} | {size} | `{source_raw}` |")
    lines.append("")

    write_report(lines)
    send_telegram("Pixel & audience check generated — see GitHub Actions summary.")


if __name__ == "__main__":
    main()
