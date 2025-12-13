from typing import Any, Dict


def call_via_gradio(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from gradio_client import Client
        client = Client("http://localhost:7860")
        if tool == "text_search":
            v = client.predict(args.get("query", ""), api_name="/text_search")
            return {"type": "text", "content": v}
        if tool == "table_stats":
            v = client.predict(
                args.get("group_by", "category"),
                args.get("metric", "revenue"),
                args.get("agg", "sum"),
                int(args.get("limit", 10)),
                api_name="/table_stats",
            )
            return {"type": "table", "columns": v["headers"], "rows": v["data"]}
        if tool == "line_series":
            v = client.predict(
                args.get("metric", "revenue"),
                args.get("start", ""),
                args.get("end", ""),
                args.get("interval", "day"),
                api_name="/line_series",
            )
            xs, ys = v[0]
            return {"type": "line", "x": xs, "y": ys}
    except Exception:
        pass
    return {"type": "error", "content": "gradio client unavailable"}

