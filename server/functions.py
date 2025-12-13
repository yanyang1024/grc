from typing import Any, Dict, List
from datetime import datetime, timedelta
from collections import defaultdict
from .data_store import SALES_DATA


def text_search(args: Dict[str, Any]) -> Dict[str, Any]:
    q = str(args.get("query", "")).lower()
    if not q:
        return {"type": "text", "content": "请输入查询内容"}
    hits = [r for r in SALES_DATA if q in r["category"].lower() or q in r["region"].lower()]
    if not hits:
        return {"type": "text", "content": "没有匹配结果"}
    total_rev = sum(h["revenue"] for h in hits)
    total_ord = sum(h["orders"] for h in hits)
    return {
        "type": "text",
        "content": f"匹配{len(hits)}条，订单{total_ord}，营收{round(total_rev,2)}",
    }


def table_stats(args: Dict[str, Any]) -> Dict[str, Any]:
    group_by = str(args.get("group_by", "category"))
    metric = str(args.get("metric", "revenue"))
    agg = str(args.get("agg", "sum"))
    limit = int(args.get("limit", 10))
    grp = defaultdict(float)
    for r in SALES_DATA:
        key = r.get(group_by)
        val = float(r.get(metric, 0))
        if agg == "sum":
            grp[key] += val
        elif agg == "avg":
            grp[key] += val
    if agg == "avg":
        counts = defaultdict(int)
        for r in SALES_DATA:
            counts[r.get(group_by)] += 1
        for k in list(grp.keys()):
            grp[k] = grp[k] / max(1, counts[k])
    items = sorted([(k, grp[k]) for k in grp.keys()], key=lambda x: x[1], reverse=True)
    items = items[:limit]
    cols = [group_by, metric]
    rows = [[k, round(v, 2)] for k, v in items]
    return {"type": "table", "columns": cols, "rows": rows}


def line_series(args: Dict[str, Any]) -> Dict[str, Any]:
    metric = str(args.get("metric", "revenue"))
    start = str(args.get("start", ""))
    end = str(args.get("end", ""))
    interval = str(args.get("interval", "day"))
    if not start or not end:
        end_dt = datetime.today().date()
        start_dt = end_dt - timedelta(days=30)
    else:
        start_dt = datetime.fromisoformat(start).date()
        end_dt = datetime.fromisoformat(end).date()
    cur = start_dt
    points = []
    while cur <= end_dt:
        if interval == "week":
            nxt = cur + timedelta(days=7)
        else:
            nxt = cur + timedelta(days=1)
        val = 0.0
        for r in SALES_DATA:
            d = datetime.fromisoformat(r["date"]).date()
            if cur <= d < nxt:
                val += float(r.get(metric, 0))
        points.append((cur.isoformat(), round(val, 2)))
        cur = nxt
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return {"type": "line", "x": xs, "y": ys, "metric": metric, "start": start_dt.isoformat(), "end": end_dt.isoformat()}


TOOLS = {
    "text_search": {
        "description": "按类别或区域的关键词检索并汇总",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
        "handler": text_search,
    },
    "table_stats": {
        "description": "按维度聚合指标并返回表格",
        "parameters": {
            "type": "object",
            "properties": {
                "group_by": {"type": "string", "default": "category"},
                "metric": {"type": "string", "default": "revenue"},
                "agg": {"type": "string", "default": "sum"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["group_by", "metric"],
        },
        "handler": table_stats,
    },
    "line_series": {
        "description": "生成时间序列折线数据",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "default": "revenue"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "interval": {"type": "string", "default": "day"},
            },
            "required": ["metric"],
        },
        "handler": line_series,
    },
}

