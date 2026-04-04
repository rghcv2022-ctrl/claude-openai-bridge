import json
import os
import time
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from bridge import (
    anthropic_request_to_openai,
    estimate_input_tokens,
    openai_response_to_anthropic,
    openai_stream_to_anthropic_events,
)


DEFAULT_CONFIG_FILE = "config.json"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"


@lru_cache(maxsize=1)
def _default_config_path():
    return Path(DEFAULT_CONFIG_FILE)


def _resolve_config_path():
    config_env = os.environ.get("CLAUDE_OPENAI_PROXY_CONFIG")
    if config_env:
        return Path(config_env)
    return _default_config_path()


def load_config():
    config_path = _resolve_config_path()
    with config_path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_openclaw_config():
    proxy_config = load_config()
    if not proxy_config.get("openclaw_mode"):
        return None
    oc_path = proxy_config.get("openclaw_config_path")
    if oc_path:
        oc_file = Path(oc_path)
    else:
        oc_file = OPENCLAW_CONFIG_PATH
    if not oc_file.exists():
        return None
    with oc_file.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def resolve_openclaw_provider(oc_config, requested_model=None):
    if oc_config is None:
        return None

    providers = oc_config.get("models", {}).get("providers", {})
    agents = oc_config.get("agents", {}).get("defaults", {})
    primary_model = agents.get("model", {}).get("primary", "")

    if not primary_model or "/" not in primary_model:
        return None

    parts = primary_model.split("/", 1)
    provider_key = parts[0]
    provider = providers.get(provider_key)
    if not provider:
        return None

    base_url = provider.get("baseUrl", "").rstrip("/")
    api_key = provider.get("apiKey", "")
    api_style = provider.get("api", "openai-completions")

    if api_style == "openai-responses":
        chat_path = "/responses"
    else:
        chat_path = "/chat/completions"

    provider_models = provider.get("models", [])
    default_model = None
    model_map = {}
    for m in provider_models:
        mid = m.get("id", "")
        model_map[mid] = m
        if default_model is None:
            default_model = mid

    if requested_model and "/" in requested_model:
        req_parts = requested_model.split("/", 1)
        if len(req_parts) == 2:
            req_model_id = req_parts[1]
            if req_model_id in model_map:
                default_model = req_model_id

    return {
        "upstream_base_url": base_url,
        "upstream_api_key": api_key,
        "upstream_chat_path": chat_path,
        "default_model": default_model or "unknown",
        "provider_key": provider_key,
        "provider_models": model_map,
    }


def build_upstream_url(config):
    return f"{config['upstream_base_url'].rstrip('/')}{config['upstream_chat_path']}"


def get_active_config(config, requested_model=None):
    oc = _load_openclaw_config()
    if oc:
        oc_resolved = resolve_openclaw_provider(oc, requested_model)
        if oc_resolved:
            merged = dict(config)
            merged.update(oc_resolved)
            return merged
    return config


def _get_retry_settings(config):
    max_attempts = int(config.get("request_retry_attempts", 2))
    if max_attempts < 1:
        max_attempts = 1
    backoff = float(config.get("request_retry_backoff_seconds", 0.5))
    if backoff < 0:
        backoff = 0
    return max_attempts, backoff


def call_upstream_json(openai_payload, config):
    max_attempts, backoff = _get_retry_settings(config)
    for attempt in range(1, max_attempts + 1):
        try:
            with httpx.Client(timeout=config["request_timeout_seconds"]) as client:
                response = client.post(
                    build_upstream_url(config),
                    headers={"Authorization": f"Bearer {config['upstream_api_key']}"},
                    json=openai_payload,
                )
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as exc:
            if (
                exc.response is not None
                and exc.response.status_code in RETRYABLE_STATUS_CODES
                and attempt < max_attempts
            ):
                time.sleep(backoff * attempt)
                continue
            raise
        except httpx.RequestError:
            if attempt < max_attempts:
                time.sleep(backoff * attempt)
                continue
            raise


def call_upstream_stream(openai_payload, config):
    max_attempts, backoff = _get_retry_settings(config)
    for attempt in range(1, max_attempts + 1):
        try:
            with httpx.Client(timeout=config["request_timeout_seconds"]) as client:
                with client.stream(
                    "POST",
                    build_upstream_url(config),
                    headers={"Authorization": f"Bearer {config['upstream_api_key']}"},
                    json=openai_payload,
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if isinstance(line, bytes):
                            line = line.decode("utf-8")
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            return
                        yield json.loads(data)
            return
        except httpx.HTTPStatusError as exc:
            if (
                exc.response is not None
                and exc.response.status_code in RETRYABLE_STATUS_CODES
                and attempt < max_attempts
            ):
                time.sleep(backoff * attempt)
                continue
            raise
        except httpx.RequestError:
            if attempt < max_attempts:
                time.sleep(backoff * attempt)
                continue
            raise


def anthropic_error_response(status_code, message, error_type="invalid_request_error"):
    return JSONResponse(
        status_code=status_code,
        content={
            "type": "error",
            "error": {
                "type": error_type,
                "message": message,
            },
        },
    )


def build_app():
    app = FastAPI()

    @app.get("/healthz")
    def healthz():
        cfg = load_config()
        oc = _load_openclaw_config()
        if oc:
            active = resolve_openclaw_provider(oc)
            if active:
                return {
                    "ok": True,
                    "listen": f"{cfg['listen_host']}:{cfg['listen_port']}",
                    "mode": "openclaw",
                    "provider": active["provider_key"],
                    "upstream_base_url": active["upstream_base_url"],
                    "default_model": active["default_model"],
                }
        return {
            "ok": True,
            "listen": f"{cfg['listen_host']}:{cfg['listen_port']}",
            "mode": "static",
            "upstream_base_url": cfg.get("upstream_base_url", ""),
            "default_model": cfg.get("default_model", ""),
        }

    @app.post("/v1/messages/count_tokens")
    async def count_tokens(request: Request):
        payload = await request.json()
        config = load_config()
        active = get_active_config(config)
        try:
            tokens = estimate_input_tokens(
                payload,
                default_model=active["default_model"],
                model_aliases=active.get(
                    "model_aliases", config.get("model_aliases", {})
                ),
            )
        except ValueError as exc:
            return anthropic_error_response(400, str(exc))
        return {"input_tokens": tokens}

    @app.post("/v1/messages")
    async def messages(request: Request):
        payload = await request.json()
        config = load_config()
        requested_model = payload.get("model")
        active = get_active_config(config, requested_model)
        try:
            openai_payload = anthropic_request_to_openai(
                payload,
                default_model=active["default_model"],
                model_aliases=active.get(
                    "model_aliases", config.get("model_aliases", {})
                ),
            )
        except ValueError as exc:
            return anthropic_error_response(400, str(exc))

        resolved_model = openai_payload.get("model")

        if openai_payload.get("stream"):

            def event_stream():
                for event in openai_stream_to_anthropic_events(
                    call_upstream_stream(openai_payload, active),
                    requested_model=requested_model,
                ):
                    yield (
                        f"event: {event['event']}\n"
                        f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                    )

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        try:
            upstream_response = call_upstream_json(openai_payload, active)
        except httpx.HTTPStatusError as exc:
            response_text = exc.response.text.strip() or str(exc)
            return anthropic_error_response(
                exc.response.status_code,
                response_text,
                error_type="api_error",
            )
        except httpx.RequestError as exc:
            return anthropic_error_response(504, str(exc), error_type="api_error")

        anthropic_payload = openai_response_to_anthropic(
            upstream_response.json(),
            requested_model=requested_model,
        )
        return JSONResponse(anthropic_payload)

    @app.post("/v1/messages/batches")
    async def message_batches():
        return JSONResponse(
            {"data": [], "has_more": False, "first_id": None, "last_id": None}
        )

    @app.get("/{rest_of_path:path}")
    async def catch_all_get():
        return JSONResponse({})

    @app.post("/{rest_of_path:path}")
    async def catch_all_post():
        return JSONResponse({})

    return app


app = build_app()
