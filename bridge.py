import fnmatch
import json

import tiktoken


def resolve_upstream_model(requested_model, default_model, model_aliases):
    if not requested_model:
        return default_model

    exact_match = model_aliases.get(requested_model)
    if exact_match:
        return exact_match

    if requested_model.startswith("gpt-"):
        return requested_model

    best_match = None
    best_score = None
    for index, (pattern, mapped_model) in enumerate(model_aliases.items()):
        if "*" not in pattern or not fnmatch.fnmatch(requested_model, pattern):
            continue

        score = (len(pattern.replace("*", "")), -pattern.count("*"), -index)
        if best_score is None or score > best_score:
            best_score = score
            best_match = mapped_model

    if best_match:
        return best_match

    return default_model


def _flatten_text_blocks(content_blocks):
    if isinstance(content_blocks, str):
        return content_blocks

    flattened = []
    for block in content_blocks or []:
        block_type = block.get("type")
        if block_type == "text":
            flattened.append(block.get("text", ""))
            continue
        if block_type == "tool_result":
            flattened.append(_flatten_text_blocks(block.get("content", [])))
            continue
        raise ValueError(f"Unsupported content block type: {block_type}")

    return "".join(flattened)


def anthropic_request_to_openai(payload, default_model, model_aliases):
    messages = []

    system = payload.get("system")
    if system is not None:
        system_content = system if isinstance(system, str) else _flatten_text_blocks(system)
        messages.append({"role": "system", "content": system_content})

    for message in payload.get("messages", []):
        role = message.get("role")
        if role == "user":
            messages.extend(_convert_user_message_content(message.get("content", [])))
            continue
        if role == "assistant":
            messages.append(_convert_assistant_message_content(message.get("content", [])))
            continue
        if role == "system":
            messages.append(
                {
                    "role": "system",
                    "content": _flatten_text_blocks(message.get("content", [])),
                }
            )
            continue
        raise ValueError(f"Unsupported message role: {role}")

    converted = {
        "model": resolve_upstream_model(
            payload.get("model"), default_model, model_aliases
        ),
        "messages": messages,
        "max_tokens": payload.get("max_tokens"),
        "temperature": payload.get("temperature"),
        "top_p": payload.get("top_p"),
        "tools": _convert_tools(payload.get("tools")),
        "tool_choice": _convert_tool_choice(payload.get("tool_choice")),
        "stop": payload.get("stop_sequences"),
        "stream": payload.get("stream"),
    }
    return _strip_none(converted)


def _convert_user_message_content(content):
    if isinstance(content, str):
        return [{"role": "user", "content": content}]

    messages = []
    text_blocks = []
    for block in content or []:
        block_type = block.get("type")
        if block_type == "text":
            text_blocks.append(block)
            continue
        if block_type == "tool_result":
            if text_blocks:
                messages.append({"role": "user", "content": _flatten_text_blocks(text_blocks)})
                text_blocks = []

            tool_content = block.get("content", [])
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": block.get("tool_use_id"),
                    "content": _flatten_text_blocks(tool_content),
                }
            )
            continue
        raise ValueError(f"Unsupported content block type: {block_type}")

    if text_blocks:
        messages.append({"role": "user", "content": _flatten_text_blocks(text_blocks)})

    return messages


def _convert_assistant_message_content(content):
    if isinstance(content, str):
        return {"role": "assistant", "content": content}

    text_blocks = []
    tool_calls = []
    for block in content or []:
        block_type = block.get("type")
        if block_type == "text":
            text_blocks.append(block)
            continue
        if block_type == "tool_use":
            tool_calls.append(
                {
                    "id": block.get("id"),
                    "type": "function",
                    "function": {
                        "name": block.get("name"),
                        "arguments": json.dumps(
                            block.get("input", {}), separators=(",", ":")
                        ),
                    },
                }
            )
            continue
        raise ValueError(f"Unsupported content block type: {block_type}")

    assistant_message = {
        "role": "assistant",
        "content": _flatten_text_blocks(text_blocks) if text_blocks else "",
    }
    if tool_calls:
        assistant_message["tool_calls"] = tool_calls
    return assistant_message


def _convert_tools(tools):
    if tools is None:
        return None

    converted_tools = []
    for tool in tools:
        converted_tools.append(
            {
                "type": "function",
                "function": _strip_none(
                    {
                        "name": tool.get("name"),
                        "description": tool.get("description"),
                        "parameters": tool.get("input_schema"),
                    }
                ),
            }
        )
    return converted_tools


def _convert_tool_choice(tool_choice):
    if tool_choice is None:
        return None

    choice_type = tool_choice.get("type")
    if choice_type == "auto":
        return "auto"
    if choice_type == "any":
        return "required"
    if choice_type == "tool":
        return {"type": "function", "function": {"name": tool_choice.get("name")}}
    return None


def _map_finish_reason(finish_reason):
    if finish_reason == "stop":
        return "end_turn"
    if finish_reason == "length":
        return "max_tokens"
    if finish_reason == "tool_calls":
        return "tool_use"
    return "end_turn"


def openai_response_to_anthropic(payload, requested_model):
    choice = payload["choices"][0]
    message = choice["message"]
    content = []

    if message.get("content"):
        content.append({"type": "text", "text": message["content"]})

    for tool_call in message.get("tool_calls", []):
        arguments = tool_call.get("function", {}).get("arguments") or "{}"
        content.append(
            {
                "type": "tool_use",
                "id": tool_call.get("id"),
                "name": tool_call.get("function", {}).get("name"),
                "input": json.loads(arguments),
            }
        )

    usage = payload.get("usage", {})
    return {
        "id": payload.get("id", "msg_proxy"),
        "type": "message",
        "role": "assistant",
        "model": requested_model or payload.get("model", ""),
        "content": content,
        "stop_reason": _map_finish_reason(choice.get("finish_reason")),
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


def estimate_input_tokens(payload, default_model, model_aliases):
    normalized = anthropic_request_to_openai(
        payload,
        default_model=default_model,
        model_aliases=model_aliases,
    )
    text = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def _strip_none(value):
    if isinstance(value, dict):
        return {
            key: _strip_none(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_strip_none(item) for item in value]
    return value
