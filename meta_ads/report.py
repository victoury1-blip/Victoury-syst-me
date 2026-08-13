from meta_ads.rules import extract_results


def build_campaign_report(client, ad_account_id, lookback_days, purchase_action_types):
    campaigns = client.list_campaigns(ad_account_id)
    rows = []
    for c in campaigns:
        insights = None
        try:
            insights = client.get_insights_full(c["id"], lookback_days)
        except Exception:
            insights = None

        spend = float(insights.get("spend", 0)) if insights else 0.0
        impressions = int(float(insights.get("impressions", 0))) if insights else 0
        clicks = int(float(insights.get("clicks", 0))) if insights else 0
        ctr = float(insights.get("ctr", 0)) if insights else 0.0
        cpc = float(insights.get("cpc", 0)) if insights else 0.0
        results = extract_results(insights, purchase_action_types)
        cpa = spend / results if results else None

        roas = None
        for r in (insights.get("purchase_roas") or []) if insights else []:
            roas = float(r.get("value", 0))
            break

        rows.append(
            {
                "id": c["id"],
                "name": c.get("name", c["id"]),
                "status": c.get("effective_status", c.get("status", "?")),
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "ctr": ctr,
                "cpc": cpc,
                "results": results,
                "cpa": cpa,
                "roas": roas,
            }
        )
    return rows


def format_report(rows, lookback_days, currency):
    period = "lifetime (since each campaign started)" if lookback_days in (None, "max", "maximum") else f"last {lookback_days} days"
    lines = [
        f"# Meta Ads Campaign Analytics — {period}",
        "",
        "| Campaign | Campaign ID | Status | Spend | Impressions | Clicks | CTR | CPC | Results | CPA | ROAS |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda x: x["spend"], reverse=True):
        cpa_str = f"{r['cpa']:.2f}" if r["cpa"] is not None else "-"
        roas_str = f"{r['roas']:.2f}" if r["roas"] is not None else "-"
        lines.append(
            f"| {r['name']} | `{r['id']}` | {r['status']} | {r['spend']:.2f} {currency} | {r['impressions']} | "
            f"{r['clicks']} | {r['ctr']:.2f}% | {r['cpc']:.2f} | {r['results']:.0f} | {cpa_str} | {roas_str} |"
        )
    return lines
