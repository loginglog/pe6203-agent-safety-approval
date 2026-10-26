"""Check local credentials and public model metadata without model inference.

Only GET /api/v1/key and GET /api/v1/models/{model}/endpoints are used.
Never print credentials, authentication headers, or service error bodies.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import tempfile

import httpx
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
MODEL = "openai/gpt-4o-mini"
BASE = "https://openrouter.ai/api/v1"


def numeric(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return str(number) if number.is_finite() and number >= 0 else None


def main():
    (ROOT / "results/raw").mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="openrouter_setup_", dir=ROOT / "results/raw"))
    record = {
        "record_type": "Read-only account and model metadata preflight; no model inference",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "openai_sdk": version("openai"),
        "model": MODEL,
        "model_api_requests": 0,
        "model_inference_cost_incurred": False,
        "credential_value_recorded": False,
        "metadata_http_requests": 0,
        "successful": False,
    }
    stage = "local_configuration"
    try:
        if record["openai_sdk"] != "3.31.0":
            raise ValueError("SDK version mismatch")
        key = os.environ.get("OPENAI_COMPATIBLE_API_KEY")
        record["credential_source"] = "environment" if key else "project_local_env"
        if not key:
            key = dotenv_values(ROOT / ".env").get("OPENAI_COMPATIBLE_API_KEY")
        record["credential_present"] = bool(key and key.strip())
        if not record["credential_present"]:
            raise ValueError("Missing local credential")
        stage = "account_metadata"
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            record["metadata_http_requests"] += 1
            response = client.get(BASE + "/key", headers={"Authorization": "Bearer " + key})
            record["account_http_status"] = response.status_code
            response.raise_for_status()
            account = response.json()["data"]
            record["account"] = {
                name: numeric(account.get(name))
                for name in ("limit", "limit_remaining", "usage", "usage_daily", "usage_weekly", "usage_monthly")
            }
            record["account"]["is_free_tier"] = account.get("is_free_tier") if type(account.get("is_free_tier")) is bool else None
            record["account"]["limit_reset"] = account.get("limit_reset") if account.get("limit_reset") in (None, "daily", "weekly", "monthly") else "other"
            stage = "public_model_metadata"
            record["pricing_source"] = BASE + "/models/" + MODEL + "/endpoints"
            record["metadata_http_requests"] += 1
            response = client.get(record["pricing_source"])
            record["model_http_status"] = response.status_code
            response.raise_for_status()
            metadata = response.json()
            # This response is public, requested without any authentication header.
            (directory / "public_model_endpoints.json").write_text(json.dumps(metadata, indent=2) + "\n")
            data = metadata["data"]
            endpoints = []
            for endpoint in data.get("endpoints", []):
                pricing = endpoint.get("pricing") or {}
                endpoints.append({
                    "provider_name": endpoint.get("provider_name"),
                    "name": endpoint.get("name"),
                    "context_length": endpoint.get("context_length"),
                    "max_completion_tokens": endpoint.get("max_completion_tokens"),
                    "prompt_usd_per_token": numeric(pricing.get("prompt")),
                    "completion_usd_per_token": numeric(pricing.get("completion")),
                    "request_usd": numeric(pricing.get("request")),
                    "supported_parameters": endpoint.get("supported_parameters"),
                    "status": endpoint.get("status"),
                })
            record["model_context_length"] = data.get("context_length")
            record["endpoints"] = endpoints
            if not endpoints:
                raise ValueError("No endpoints returned")
        record["successful"] = True
    except Exception as exc:
        record["error"] = {"stage": stage, "category": type(exc).__name__}
    record["log_directory"] = str(directory.relative_to(ROOT))
    (directory / "summary.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return 0 if record["successful"] else 1


if __name__ == "__main__":
    sys.exit(main())
