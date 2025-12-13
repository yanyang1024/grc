import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]


class MCP:
    def __init__(self, model: str, use_gradio_client: bool = False):
        self.model = model
        self.tools: Dict[str, ToolSpec] = {}
        self.use_gradio_client = use_gradio_client

    def register(self, tool: ToolSpec) -> None:
        self.tools[tool.name] = tool

    def _system_prompt(self) -> str:
        tools_json = []
        for t in self.tools.values():
            tools_json.append(
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            )
        spec = {
            "tools": tools_json,
            "response_schema": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "arguments": {"type": "object"},
                },
                "required": ["tool", "arguments"],
                "additionalProperties": False,
            },
        }
        return (
            "You select a single tool and return only JSON that matches the response_schema. "
            + json.dumps(spec, ensure_ascii=False)
        )

    def _chat(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                msg = data.get("message", {})
                content = msg.get("content")
                if isinstance(content, list):
                    content = "".join([c.get("text", c.get("content", "")) if isinstance(c, dict) else str(c) for c in content])
                if content is None:
                    content = ""
                return content
        except urllib.error.URLError:
            return "{}"

    def _validate(self, tool: ToolSpec, args: Dict[str, Any]) -> Dict[str, Any]:
        schema = tool.parameters
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for k in required:
            if k not in args:
                default = props.get(k, {}).get("default")
                if default is not None:
                    args[k] = default
        for k, v in list(args.items()):
            if k in props:
                typ = props[k].get("type")
                if typ == "string" and not isinstance(v, str):
                    args[k] = str(v)
                if typ == "integer" and not isinstance(v, int):
                    try:
                        args[k] = int(v)
                    except Exception:
                        args[k] = props[k].get("default", 0)
        return args

    def plan(self, user_input: str) -> Optional[Dict[str, Any]]:
        system = {"role": "system", "content": self._system_prompt()}
        user = {"role": "user", "content": user_input}
        raw = self._chat([system, user])
        try:
            obj = json.loads(raw)
        except Exception:
            raw2 = self._chat([system, {"role": "user", "content": user_input + " Return only JSON."}])
            try:
                obj = json.loads(raw2)
            except Exception:
                return None
        name = obj.get("tool")
        args = obj.get("arguments", {})
        if name not in self.tools:
            return None
        spec = self.tools[name]
        args = self._validate(spec, args)
        return {"name": name, "arguments": args}

    def call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if self.use_gradio_client:
            try:
                from clients.gradio_bridge import call_via_gradio
                return call_via_gradio(name, args)
            except Exception:
                pass
        tool = self.tools[name]
        return tool.handler(args)

    def run(self, user_input: str) -> Dict[str, Any]:
        plan = self.plan(user_input)
        if not plan:
            return {"type": "text", "content": "未能解析请求"}
        return self.call(plan["name"], plan["arguments"])

