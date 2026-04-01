from fastapi.testclient import TestClient

import app


def _make_test_config():
    return {
        "listen_host": "127.0.0.1",
        "listen_port": 43118,
        "upstream_base_url": "https://gmncode.cn/v1",
        "upstream_api_key": "sk-test",
        "upstream_chat_path": "/chat/completions",
        "default_model": "gpt-5.4",
        "request_timeout_seconds": 600,
        "log_level": "INFO",
        "model_aliases": {"claude-*": "gpt-5.4"},
    }


def test_count_tokens_endpoint_returns_anthropic_shape(monkeypatch):
    monkeypatch.setattr(app, "load_config", _make_test_config)
    monkeypatch.setattr(
        app,
        "estimate_input_tokens",
        lambda payload, default_model, model_aliases: 77,
    )

    client = TestClient(app.build_app())
    response = client.post(
        "/v1/messages/count_tokens",
        json={"messages": [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]},
    )

    assert response.status_code == 200
    assert response.json() == {"input_tokens": 77}


def test_messages_endpoint_returns_upstream_json_for_non_stream(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "id": "chatcmpl_123",
                "model": "gpt-5.4",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "OK"},
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 2},
            }

        def raise_for_status(self):
            return None

    monkeypatch.setattr(app, "call_upstream_json", lambda openai_payload, config: FakeResponse())
    monkeypatch.setattr(app, "load_config", _make_test_config)

    client = TestClient(app.build_app())
    response = client.post(
        "/v1/messages",
        json={
            "model": "claude-3-7-sonnet-20250219",
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Ping"}]}],
        },
    )

    assert response.status_code == 200
    assert response.json()["content"][0]["text"] == "OK"
    assert response.json()["model"] == "claude-3-7-sonnet-20250219"


def test_messages_endpoint_streams_anthropic_events(monkeypatch):
    monkeypatch.setattr(
        app,
        "call_upstream_stream",
        lambda openai_payload, config: iter(
            [
                {
                    "id": "chatcmpl_1",
                    "model": "gpt-5.4",
                    "choices": [
                        {"delta": {"role": "assistant", "content": "OK"}, "index": 0}
                    ],
                },
                {
                    "id": "chatcmpl_1",
                    "model": "gpt-5.4",
                    "choices": [{"delta": {}, "index": 0, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 1},
                },
            ]
        ),
    )
    monkeypatch.setattr(app, "load_config", _make_test_config)

    client = TestClient(app.build_app())
    response = client.post(
        "/v1/messages",
        json={
            "model": "claude-3-7-sonnet-20250219",
            "stream": True,
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Ping"}]}],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message_start" in response.text
    assert "event: message_stop" in response.text
