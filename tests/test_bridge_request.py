import pytest

from bridge import anthropic_request_to_openai, resolve_upstream_model


def test_anthropic_request_to_openai_full_conversion():
    payload = {
        "model": "claude-sonnet-4-5",
        "system": "You are helpful.",
        "max_tokens": 256,
        "temperature": 0.2,
        "top_p": 0.9,
        "stream": True,
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "Check weather"}]},
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "get_weather",
                        "input": {"city": "Shanghai"},
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_1",
                        "content": [
                            {"type": "text", "text": "Sunny"},
                            {
                                "type": "tool_result",
                                "tool_use_id": "nested_1",
                                "content": [{"type": "text", "text": " with breeze"}],
                            },
                        ],
                    }
                ],
            },
        ],
        "tools": [
            {
                "name": "get_weather",
                "description": "Get current weather",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            }
        ],
        "tool_choice": {"type": "any"},
        "stop_sequences": ["\n\nHuman:"],
    }

    converted = anthropic_request_to_openai(
        payload=payload,
        default_model="gpt-default",
        model_aliases={"claude-sonnet*": "gpt-5.4", "claude-*": "gpt-fallback"},
    )

    assert converted == {
        "model": "gpt-5.4",
        "messages": [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Check weather"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "toolu_1",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"city":"Shanghai"}',
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "toolu_1", "content": "Sunny with breeze"},
        ],
        "max_tokens": 256,
        "temperature": 0.2,
        "top_p": 0.9,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }
        ],
        "tool_choice": "required",
        "stop": ["\n\nHuman:"],
        "stream": True,
    }


def test_anthropic_request_to_openai_maps_auto_tool_choice():
    payload = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Ping"}]}],
        "tools": [{"name": "echo", "input_schema": {"type": "object"}}],
        "tool_choice": {"type": "auto"},
    }

    converted = anthropic_request_to_openai(payload, "gpt-default", {})

    assert converted["tool_choice"] == "auto"
    assert converted["model"] == "gpt-default"
    assert converted["messages"] == [{"role": "user", "content": "Ping"}]


def test_anthropic_request_to_openai_maps_named_tool_choice_to_function():
    payload = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Ping"}]}],
        "tools": [{"name": "echo", "input_schema": {"type": "object"}}],
        "tool_choice": {"type": "tool", "name": "echo"},
    }

    converted = anthropic_request_to_openai(payload, "gpt-default", {})

    assert converted["tool_choice"] == {
        "type": "function",
        "function": {"name": "echo"},
    }


def test_anthropic_request_to_openai_raises_on_unknown_content_block():
    payload = {
        "messages": [{"role": "user", "content": [{"type": "image", "source": {}}]}]
    }

    with pytest.raises(ValueError, match="Unsupported content block type: image"):
        anthropic_request_to_openai(payload, "gpt-default", {})


def test_anthropic_request_to_openai_supports_system_message_role():
    payload = {
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": "Stay concise."}]},
            {"role": "user", "content": [{"type": "text", "text": "Ping"}]},
        ]
    }

    converted = anthropic_request_to_openai(payload, "gpt-default", {})

    assert converted["messages"] == [
        {"role": "system", "content": "Stay concise."},
        {"role": "user", "content": "Ping"},
    ]


def test_anthropic_request_to_openai_raises_on_unknown_role():
    payload = {"messages": [{"role": "developer", "content": [{"type": "text", "text": "x"}]}]}

    with pytest.raises(ValueError, match="Unsupported message role: developer"):
        anthropic_request_to_openai(payload, "gpt-default", {})


def test_resolve_upstream_model_prefers_more_specific_wildcard_and_fallback_rules():
    aliases = {"claude-*": "gpt-wide", "claude-sonnet*": "gpt-sonnet"}

    assert (
        resolve_upstream_model("claude-sonnet-4-5", "gpt-default", aliases)
        == "gpt-sonnet"
    )
    assert resolve_upstream_model("gpt-5.4-mini", "gpt-default", aliases) == "gpt-5.4-mini"
    assert resolve_upstream_model("unknown-model", "gpt-default", aliases) == "gpt-default"
    assert resolve_upstream_model(None, "gpt-default", aliases) == "gpt-default"
