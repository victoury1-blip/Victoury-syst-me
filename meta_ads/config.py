import os

import yaml

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config(path=DEFAULT_CONFIG_PATH):
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def load_secrets():
    access_token = os.environ.get("META_ACCESS_TOKEN")
    ad_account_id = os.environ.get("META_AD_ACCOUNT_ID")
    if not access_token or not ad_account_id:
        raise RuntimeError(
            "META_ACCESS_TOKEN and META_AD_ACCOUNT_ID must be set as environment variables "
            "(GitHub Actions secrets or a local .env)"
        )
    if not ad_account_id.startswith("act_"):
        ad_account_id = f"act_{ad_account_id}"
    return {"access_token": access_token, "ad_account_id": ad_account_id}
