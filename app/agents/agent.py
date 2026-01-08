import json
from app.services.groq_client import groq_chat
from app.agents.tool_schema import tools
from app.agents.tools_runtime import (
    tool_search_policy,
    tool_get_parks,
    tool_get_plots,
    tool_find_nearby_pois
)
from app.agents.tool_compressor import compress_tool_result
from app.utils.state import normalize_state

TOOL_MAP = {
    "search_policy": tool_search_policy,
    "get_parks": tool_get_parks,
    "get_plots": tool_get_plots,
    "find_nearby_pois": tool_find_nearby_pois
}

SYSTEM_PROMPT = """
You are an industrial policy expert assistant.

Rules:
- Use tools to fetch facts.
- Do NOT hallucinate parks or incentives.
- Base conclusions on policy + data.
- Cite policy pages if used.
"""

def run_agent(state: str, user_question: str):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_question}
    ]

    response = groq_chat(messages, tools=tools)
    msg = response.choices[0].message

    if msg.tool_calls:
        tool_messages = []

        for call in msg.tool_calls:
            name = call.function.name
            raw_args = call.function.arguments
            tool_call_id = call.id

            # ---- Normalize args ONCE ----
            if raw_args is None:
                args = {}
            elif isinstance(raw_args, str):
                cleaned = raw_args.strip()
                args = json.loads(cleaned) if cleaned else {}
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}

            # ---- GUARANTEE state exists ----
            args.setdefault("state", state)
            args["state"] = normalize_state(args["state"])

            print(f"[AGENT][TOOL_CALL] name={name} args={args}")

            # ---- Call tool EXACTLY as schema expects ----
            result = TOOL_MAP[name](**args)

            compressed = compress_tool_result(name, result)

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": compressed
            })

        messages.extend(tool_messages)

        final = groq_chat(messages)

        return {
            "answer": final.choices[0].message.content,
            "tools_used": [call.function.name for call in msg.tool_calls]
        }

    return {"answer": msg.content}

