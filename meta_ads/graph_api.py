import json
from datetime import date, timedelta

import requests

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

_DATE_PRESETS = {1: "yesterday", 3: "last_3d", 7: "last_7d", 14: "last_14d", 28: "last_28d"}


class MetaGraphError(RuntimeError):
    pass


class MetaGraphClient:
    def __init__(self, access_token):
        self.access_token = access_token

    def _get(self, path, params=None):
        params = dict(params or {})
        params["access_token"] = self.access_token
        resp = requests.get(f"{GRAPH_API_BASE}/{path}", params=params, timeout=30)
        data = resp.json()
        if resp.status_code >= 400 or "error" in data:
            raise MetaGraphError(data.get("error", data))
        return data

    def _post(self, path, data=None):
        payload = dict(data or {})
        payload["access_token"] = self.access_token
        resp = requests.post(f"{GRAPH_API_BASE}/{path}", data=payload, timeout=30)
        result = resp.json()
        if resp.status_code >= 400 or "error" in result:
            raise MetaGraphError(result.get("error", result))
        return result

    def list_active_ad_sets(self, ad_account_id, campaign_ids=None):
        params = {
            "fields": "id,name,status,effective_status,daily_budget,campaign_id",
            "effective_status": '["ACTIVE"]',
            "limit": 200,
        }
        data = self._get(f"{ad_account_id}/adsets", params=params)
        ad_sets = data.get("data", [])
        if campaign_ids:
            ad_sets = [a for a in ad_sets if a.get("campaign_id") in campaign_ids]
        return ad_sets

    def get_ad_set(self, ad_set_id):
        return self._get(ad_set_id, params={"fields": "id,name,status,daily_budget,campaign_id"})

    def list_campaigns(self, ad_account_id):
        params = {
            "fields": "id,name,objective,status,effective_status,daily_budget,lifetime_budget",
            "limit": 200,
        }
        data = self._get(f"{ad_account_id}/campaigns", params=params)
        return data.get("data", [])

    @staticmethod
    def _time_range(lookback_days):
        until = date.today() - timedelta(days=1)
        since = until - timedelta(days=max(lookback_days, 1) - 1)
        return json.dumps({"since": since.isoformat(), "until": until.isoformat()})

    def get_insights(self, object_id, lookback_days):
        params = {
            "fields": "spend,actions",
            "time_range": self._time_range(lookback_days),
        }
        data = self._get(f"{object_id}/insights", params=params)
        rows = data.get("data", [])
        return rows[0] if rows else None

    def get_insights_full(self, object_id, lookback_days):
        params = {"fields": "spend,actions,impressions,clicks,ctr,cpc,cpm,reach,purchase_roas"}
        if lookback_days in (None, "max", "maximum"):
            # Meta's own "maximum" date preset — everything available for this
            # object, i.e. lifetime since the campaign/ad set was created
            # (API limits this to roughly the last 37 months).
            params["date_preset"] = "maximum"
        else:
            params["time_range"] = self._time_range(lookback_days)
        data = self._get(f"{object_id}/insights", params=params)
        rows = data.get("data", [])
        return rows[0] if rows else None

    def update_daily_budget(self, ad_set_id, new_budget_minor_units):
        return self._post(ad_set_id, data={"daily_budget": int(new_budget_minor_units)})

    def pause_ad_set(self, ad_set_id):
        return self._post(ad_set_id, data={"status": "PAUSED"})

    def get_campaign_by_name(self, ad_account_id, name):
        for c in self.list_campaigns(ad_account_id):
            if c.get("name") == name:
                return c
        return None

    def copy_campaign(self, campaign_id, rename_suffix, deep_copy=True, status_option="PAUSED"):
        data = {
            "deep_copy": "true" if deep_copy else "false",
            "status_option": status_option,
            "rename_options": json.dumps(
                {"rename_strategy": "DEEP_RENAME", "rename_suffix": rename_suffix}
            ),
        }
        return self._post(f"{campaign_id}/copies", data=data)

    def list_custom_audiences(self, ad_account_id):
        params = {
            "fields": "id,name,subtype,approximate_count_lower_bound,approximate_count_upper_bound,data_source,description",
            "limit": 200,
        }
        data = self._get(f"{ad_account_id}/customaudiences", params=params)
        return data.get("data", [])

    def list_ad_sets_for_campaign(self, campaign_id):
        params = {
            "fields": "id,name,status,effective_status,daily_budget,targeting,optimization_goal,billing_event",
            "limit": 200,
        }
        data = self._get(f"{campaign_id}/adsets", params=params)
        return data.get("data", [])

    def list_ads_for_campaign(self, campaign_id):
        params = {
            "fields": (
                "id,name,status,effective_status,"
                "creative{title,body,call_to_action_type,thumbnail_url,object_story_spec}"
            ),
            "limit": 200,
        }
        data = self._get(f"{campaign_id}/ads", params=params)
        return data.get("data", [])
