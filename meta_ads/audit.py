from meta_ads.rules import extract_results

# Each funnel step has its own set of overlapping action_types, same problem
# as purchases: Meta reports one real event under several names at once, so
# extract_results() (first match, not sum) is reused here too.
FUNNEL_STEPS = [
    ("View Content", ["omni_view_content", "offsite_conversion.fb_pixel_view_content", "view_content"]),
    ("Add to Cart", ["omni_add_to_cart", "offsite_conversion.fb_pixel_add_to_cart", "add_to_cart"]),
    (
        "Initiate Checkout",
        [
            "omni_initiated_checkout",
            "offsite_conversion.fb_pixel_initiate_checkout",
            "initiate_checkout",
        ],
    ),
]


def format_audience_size(audience):
    lo = audience.get("approximate_count_lower_bound")
    hi = audience.get("approximate_count_upper_bound")
    if lo is None and hi is None:
        return "-"
    if lo == hi or hi is None:
        return f"{lo}"
    return f"{lo}-{hi}"


def format_targeting(targeting):
    if not targeting:
        return "-"
    parts = []

    age_min = targeting.get("age_min")
    age_max = targeting.get("age_max")
    if age_min or age_max:
        parts.append(f"Age {age_min or '?'}-{age_max or '?'}")

    genders = targeting.get("genders")
    if genders:
        gender_names = {1: "Men", 2: "Women"}
        parts.append("Gender " + ",".join(gender_names.get(g, str(g)) for g in genders))

    geo = targeting.get("geo_locations") or {}
    countries = geo.get("countries")
    if countries:
        parts.append("Countries " + ",".join(countries))

    flexible = targeting.get("flexible_spec") or []
    interest_names = []
    for spec in flexible:
        for interest in spec.get("interests", []) or []:
            if interest.get("name"):
                interest_names.append(interest["name"])
    if interest_names:
        parts.append("Interests: " + ", ".join(interest_names))

    custom_audiences = targeting.get("custom_audiences")
    if custom_audiences:
        parts.append("Custom Audiences: " + ", ".join(str(c.get("id")) for c in custom_audiences))

    excluded = targeting.get("excluded_custom_audiences")
    if excluded:
        parts.append("Excludes: " + ", ".join(str(c.get("id")) for c in excluded))

    placements = targeting.get("publisher_platforms")
    if placements:
        parts.append("Placements: " + ",".join(placements))

    return "; ".join(parts) if parts else "-"


def format_creative(ad):
    creative = ad.get("creative") or {}
    story = creative.get("object_story_spec") or {}
    link_data = story.get("link_data") or {}

    text = creative.get("body") or link_data.get("message") or "-"
    cta = creative.get("call_to_action_type")
    if not cta:
        cta = (link_data.get("call_to_action") or {}).get("type", "-")
    link = link_data.get("link", "-")

    return text, cta or "-", link


def build_audit(client, ad_account_id, lookback_days, purchase_action_types, min_spend_for_history):
    audiences = client.list_custom_audiences(ad_account_id)

    campaigns = client.list_campaigns(ad_account_id)
    scored = []
    for c in campaigns:
        insights = client.get_insights_full(c["id"], lookback_days)
        spend = float(insights.get("spend", 0)) if insights else 0.0
        roas = None
        for r in (insights.get("purchase_roas") or []) if insights else []:
            roas = float(r.get("value", 0))
            break
        scored.append({"campaign": c, "spend": spend, "roas": roas})

    active = [s for s in scored if s["campaign"].get("effective_status") == "ACTIVE"]
    historical = sorted(
        (s for s in scored if s["campaign"].get("effective_status") != "ACTIVE" and s["spend"] >= min_spend_for_history),
        key=lambda s: (s["roas"] or 0),
        reverse=True,
    )[:5]
    target_campaigns = [s["campaign"] for s in active] + [s["campaign"] for s in historical]

    campaign_details = []
    for campaign in target_campaigns:
        ad_sets = client.list_ad_sets_for_campaign(campaign["id"])
        ad_set_details = []
        for ad_set in ad_sets:
            funnel_insights = client.get_insights_full(ad_set["id"], lookback_days)
            spend = float(funnel_insights.get("spend", 0)) if funnel_insights else 0.0
            funnel = [(name, extract_results(funnel_insights, types)) for name, types in FUNNEL_STEPS]
            purchases = extract_results(funnel_insights, purchase_action_types)
            ad_set_details.append(
                {
                    "ad_set": ad_set,
                    "spend": spend,
                    "funnel": funnel,
                    "purchases": purchases,
                }
            )
        ads = client.list_ads_for_campaign(campaign["id"])
        campaign_details.append({"campaign": campaign, "ad_sets": ad_set_details, "ads": ads})

    return audiences, campaign_details


def format_audit(audiences, campaign_details, currency):
    lines = ["# Meta Ads Deep Audit — Audiences, Targeting, Creative & Funnel", ""]

    lines += ["## Custom Audiences", "", "| Name | Subtype | Approx. size | Source |", "|---|---|---|---|"]
    for a in audiences:
        source = (a.get("data_source") or {}).get("type", "-")
        lines.append(f"| {a.get('name', '-')} | {a.get('subtype', '-')} | {format_audience_size(a)} | {source} |")
    lines.append("")

    for detail in campaign_details:
        c = detail["campaign"]
        lines.append(f"## {c.get('name')} — `{c['id']}` ({c.get('effective_status', c.get('status', '?'))})")
        lines.append("")

        for ad_set_detail in detail["ad_sets"]:
            ad_set = ad_set_detail["ad_set"]
            lines.append(f"**Ad Set: {ad_set.get('name')}** (`{ad_set['id']}`)")
            lines.append(
                f"- Optimization goal: {ad_set.get('optimization_goal', '-')}, "
                f"Billing event: {ad_set.get('billing_event', '-')}"
            )
            lines.append(f"- Targeting: {format_targeting(ad_set.get('targeting'))}")
            funnel_str = " -> ".join(f"{name}: {value:.0f}" for name, value in ad_set_detail["funnel"])
            lines.append(
                f"- Funnel: {funnel_str} -> Purchase: {ad_set_detail['purchases']:.0f} "
                f"(Spend {ad_set_detail['spend']:.2f} {currency})"
            )
            lines.append("")

        ads = detail["ads"]
        if ads:
            lines.append("| Ad | Text | CTA | Link |")
            lines.append("|---|---|---|---|")
            for ad in ads:
                text, cta, link = format_creative(ad)
                text_short = (text[:100] + "…") if len(text) > 100 else text
                text_short = text_short.replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {ad.get('name')} | {text_short} | {cta} | {link} |")
            lines.append("")

    return lines
