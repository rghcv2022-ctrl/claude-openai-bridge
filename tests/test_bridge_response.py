from bridge import estimate_input_tokens, openai_response_to_anthropic


def test_non_stream_response_maps_text_tool_calls_and_usage():
    payload = {
        "id": "chatcmpl_123",
        "model": "gpt-5.4",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": "I will read the file.",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": "{\"path\": \"notes.txt\"}",
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 21, "completion_tokens": 9},
    }

    result = openai_response_to_anthropic(
        payload, requested_model="claude-3-7-sonnet-20250219"
    )

    assert result["type"] == "message"
    assert result["model"] == "claude-3-7-sonnet-20250219"
    assert result["stop_reason"] == "tool_use"
    assert result["usage"] == {"input_tokens": 21, "output_tokens": 9}
    assert result["content"][0] == {
        "type": "text",
        "text": "I will read the file.",
    }
    assert result["content"][1] == {
        "type": "tool_use",
        "id": "call_1",
        "name": "read_file",
        "input": {"path": "notes.txt"},
    }


def test_count_tokens_returns_stable_positive_integer():
    payload = {
        "system": "You are helpful.",
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Summarize this paragraph."}],
            }
        ],
    }

    tokens = estimate_input_tokens(
        payload,
        default_model="gpt-5.4",
        model_aliases={"claude-*": "gpt-5.4"},
    )

    assert isinstance(tokens, int)
    assert tokens > 0
