import os
from typing import Any, Dict, List, Tuple


def build_original_tab(gr):
    from .functions import text_search, table_stats, line_series
    with gr.Tab("原始应用"):
        with gr.Row():
            with gr.Column():
                inp = gr.Textbox(label="关键词")
                out = gr.Textbox(label="结果")
                btn = gr.Button("查询")
                btn.click(lambda q: text_search({"query": q})["content"], inp, out, api_name="/text_search")
        with gr.Row():
            with gr.Column():
                g = gr.Dropdown(choices=["category", "region"], value="category", label="分组维度")
                m = gr.Dropdown(choices=["revenue", "orders"], value="revenue", label="指标")
                a = gr.Dropdown(choices=["sum", "avg"], value="sum", label="聚合方式")
                l = gr.Slider(1, 50, value=10, step=1, label="TopK")
                out = gr.Dataframe(label="表格结果")
                btn = gr.Button("统计")
                def run_table(gb, mm, aa, ll):
                    res = table_stats({"group_by": gb, "metric": mm, "agg": aa, "limit": int(ll)})
                    return {"data": res["rows"], "headers": res["columns"]}
                btn.click(run_table, [g, m, a, l], out, api_name="/table_stats")
        with gr.Row():
            with gr.Column():
                metric = gr.Dropdown(choices=["revenue", "orders"], value="revenue", label="指标")
                start = gr.Textbox(placeholder="YYYY-MM-DD", label="开始日期")
                end = gr.Textbox(placeholder="YYYY-MM-DD", label="结束日期")
                interval = gr.Dropdown(choices=["day", "week"], value="day", label="粒度")
                out = gr.LinePlot(label="折线图")
                btn = gr.Button("生成")
                def run_line(mm, ss, ee, ii):
                    res = line_series({"metric": mm, "start": ss, "end": ee, "interval": ii})
                    xs = res["x"]
                    ys = res["y"]
                    return [(xs, ys)]
                btn.click(run_line, [metric, start, end, interval], out, api_name="/line_series")


def build_chat_tab(gr):
    from mcp.engine import MCP, ToolSpec
    from server.functions import TOOLS
    with gr.Tab("对话式应用"):
        chat = gr.Chatbot()
        inp = gr.Textbox()
        text_out = gr.Textbox(label="文本输出")
        table_out = gr.Dataframe(label="表格输出")
        line_out = gr.LinePlot(label="折线输出")
        send = gr.Button("发送")
        def run_chat(msg: str, history: List[Tuple[str, str]]):
            m = MCP(model=os.environ.get("MCP_MODEL", "qwen3:8b"), use_gradio_client=True)
            for name, t in TOOLS.items():
                m.register(ToolSpec(name=name, description=t["description"], parameters=t["parameters"], handler=t["handler"]))
            res = m.run(msg)
            if res.get("type") == "table":
                table_val = {"data": res.get("rows", []), "headers": res.get("columns", [])}
                line_val = []
                text_val = "表格已生成"
            elif res.get("type") == "line":
                xs = res.get("x", [])
                ys = res.get("y", [])
                table_val = {"data": [], "headers": []}
                line_val = [(xs, ys)]
                text_val = "折线已生成"
            else:
                table_val = {"data": [], "headers": []}
                line_val = []
                text_val = res.get("content", "")
            history = (history or []) + [(msg, text_val)]
            return history, text_val, table_val, line_val
        send.click(run_chat, [inp, chat], [chat, text_out, table_out, line_out])


def build_interface():
    import gradio as gr
    with gr.Blocks() as demo:
        with gr.Tabs():
            build_original_tab(gr)
            build_chat_tab(gr)
    return demo


def main():
    demo = build_interface()
    host = os.environ.get("GRADIO_HOST", "0.0.0.0")
    port = int(os.environ.get("GRADIO_PORT", "7860"))
    demo.launch(server_name=host, server_port=port)


if __name__ == "__main__":
    main()

