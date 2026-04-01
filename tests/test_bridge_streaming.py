from bridge import openai_stream_to_anthropic_events


def test_stream_translation_emits_message_text_tool_and_stop_events():
    chunks = [
        {
            "id": "chatcmpl_1",
            "model": "gpt-5.4",
            "choices": [{"delta": {"role": "assistant", "content": "Hello"}, "index": 0}],
        },
        {
            "id": "chatcmpl_1",
            "model": "gpt-5.4",
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "function": {
                                    "name": "read_file",
                                    "arguments": "{\"path\":\"a",
                                },
                            }
                        ]
                    },
                    "index": 0,
                }
            ],
        },
        {
            "id": "chatcmpl_1",
            "model": "gpt-5.4",
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "function": {"arguments": ".txt\"}"},
                            }
                        ]
                    },
                    "index": 0,
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 30, "completion_tokens": 11},
        },
    ]

    events = list(
        openai_stream_to_anthropic_events(
            chunks, requested_model="claude-3-7-sonnet-20250219"
        )
    )
    event_names = [event["event"] for event in events]

    assert event_names == [
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "content_block_start",
        "content_block_delta",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    assert events[1]["data"]["content_block"]["type"] == "text"
    assert events[4]["data"]["content_block"]["type"] == "tool_use"
    assert events[8]["data"]["delta"]["stop_reason"] == "tool_use"
