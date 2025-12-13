import json
from typing import Dict
import os
from mcp.engine import MCP, ToolSpec
from server.functions import TOOLS


def build_mcp(model: str) -> MCP:
    use_gc = os.environ.get("USE_GRADIO_CLIENT", "0") in ("1", "true", "True")
    m = MCP(model=model, use_gradio_client=use_gc)
    for name, t in TOOLS.items():
        m.register(
            ToolSpec(
                name=name,
                description=t["description"],
                parameters=t["parameters"],
                handler=t["handler"],
            )
        )
    return m


def format_output(res: Dict) -> str:
    if res.get("type") == "text":
        return res.get("content", "")
    if res.get("type") == "table":
        cols = res.get("columns", [])
        rows = res.get("rows", [])
        head = " | ".join([str(c) for c in cols])
        sep = "-+-".join(["-" * len(str(c)) for c in cols])
        lines = [head, sep]
        for r in rows:
            lines.append(" | ".join([str(x) for x in r]))
        return "\n".join(lines)
    if res.get("type") == "line":
        xs = res.get("x", [])
        ys = res.get("y", [])
        if not ys:
            return ""
        min_y = min(ys)
        max_y = max(ys)
        rng = max(1, int(max_y - min_y))
        blocks = "▁▂▃▄▅▆▇"
        def scale(v):
            idx = int((v - min_y) / rng * (len(blocks) - 1))
            return blocks[idx]
        spark = "".join(scale(v) for v in ys)
        return spark
    return json.dumps(res, ensure_ascii=False)


def main():
    model = "qwen3:8b"
    m = build_mcp(model)
    while True:
        try:
            q = input("> ")
        except EOFError:
            break
        if not q:
            continue
        res = m.run(q)
        print(format_output(res))


if __name__ == "__main__":
    main()
