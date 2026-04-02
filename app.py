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


def build_upstream_url(config):
    return f"{config['upstream_base_url'].rstrip('/')}{config['upstream_chat_path']}"

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
        return {
            "ok": True,
            "listen": f'{cfg["listen_host"]}:{cfg["listen_port"]}',
            "upstream_base_url": cfg["upstream_base_url"],
            "default_model": cfg["default_model"],
        }

    @app.post("/v1/messages/count_tokens")
    async def count_tokens(request: Request):
        payload = await request.json()
        config = load_config()
        try:
            tokens = estimate_input_tokens(
                payload,
                default_model=config["default_model"],
                model_aliases=config["model_aliases"],
            )
        except ValueError as exc:
            return anthropic_error_response(400, str(exc))
        return {"input_tokens": tokens}

    @app.post("/v1/messages")
    async def messages(request: Request):
        payload = await request.json()
        config = load_config()
        try:
            openai_payload = anthropic_request_to_openai(
                payload,
                default_model=config["default_model"],
                model_aliases=config["model_aliases"],
            )
        except ValueError as exc:
            return anthropic_error_response(400, str(exc))

        requested_model = payload.get("model") or openai_payload.get("model")

        if openai_payload.get("stream"):
            def event_stream():
                for event in openai_stream_to_anthropic_events(
                    call_upstream_stream(openai_payload, config),
                    requested_model=requested_model,
                ):
                    yield (
                        f"event: {event['event']}\n"
                        f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                    )

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        try:
            upstream_response = call_upstream_json(openai_payload, config)
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

    return app


app = build_app()
