import json
import httpx
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agent.tools import TOOLS
from config import settings

SYSTEM_PROMPT = """You are a personal AI assistant with access to the user's private document library.
You have tools to search, read, list, and summarize documents. 
Always use the search tool first to find relevant documents before answering.
When summarizing, be concise and structured. Respond in the same language as the user's question.

Available tools:
- search(query, top_k): Semantic search across all indexed documents
- read_file(rel_path): Read a specific document by path
- summarize(rel_path): Get content of a file to summarize
- list_files(subfolder, ext): Browse available files

To use a tool, respond with JSON in this exact format (nothing else on that line):
TOOL: {"name": "tool_name", "args": {"arg1": "value1"}}

After getting tool results, provide your final answer to the user."""

def _call_ollama(messages: list, model: str = None) -> str:
    model = model or settings.chat_model
    r = httpx.post(
        f"{settings.ollama_base_url}/api/chat",
        json={"model": model, "messages": messages, "stream": False},
        timeout=120
    )
    r.raise_for_status()
    return r.json()["message"]["content"]

def _execute_tool(name: str, args: dict) -> str:
    if name not in TOOLS:
        return f"Unknown tool: {name}"
    try:
        result = TOOLS[name]["fn"](**args)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Tool error: {e}"

def chat(user_message: str, history: list = None, model: str = None) -> dict:
    used_model = model or settings.chat_model
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    tool_calls = []
    max_iterations = 5

    for _ in range(max_iterations):
        response = _call_ollama(messages, model=used_model)

        tool_line = None
        for line in response.split("\n"):
            if line.strip().startswith("TOOL:"):
                tool_line = line.strip()[5:].strip()
                break

        if not tool_line:
            return {
                "answer": response,
                "tool_calls": tool_calls,
                "model": used_model
            }

        try:
            tool_req = json.loads(tool_line)
            tool_name = tool_req["name"]
            tool_args = tool_req.get("args", {})
            tool_result = _execute_tool(tool_name, tool_args)
            tool_calls.append({"tool": tool_name, "args": tool_args})

            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": f"Tool result for {tool_name}:\n{tool_result}\n\nNow provide your answer."
            })
        except json.JSONDecodeError:
            return {"answer": response, "tool_calls": tool_calls, "model": used_model}

    return {"answer": response, "tool_calls": tool_calls, "model": used_model}
