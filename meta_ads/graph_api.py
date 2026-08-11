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

    def get_insights(self, ad_set_id, lookback_days):
        until = date.today() - timedelta(days=1)
        since = until - timedelta(days=max(lookback_days, 1) - 1)
        params = {
            "fields": "spend,actions",
            "time_range": json.dumps({"since": since.isoformat(), "until": until.isoformat()}),
        }
        data = self._get(f"{ad_set_id}/insights", params=params)
        rows = data.get("data", [])
        return rows[0] if rows else None

    def update_daily_budget(self, ad_set_id, new_budget_minor_units):
        return self._post(ad_set_id, data={"daily_budget": int(new_budget_minor_units)})

    def pause_ad_set(self, ad_set_id):
        return self._post(ad_set_id, data={"status": "PAUSED"})
