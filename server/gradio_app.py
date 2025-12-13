import os
from typing import Any, Dict


def build_interface():
    import gradio as gr
    from .functions import text_search, table_stats, line_series
    with gr.Blocks() as demo:
        with gr.Tabs():
            with gr.Tab("文本"):
                inp = gr.Textbox()
                out = gr.Textbox()
                btn = gr.Button("查询")
                btn.click(lambda q: text_search({"query": q})["content"], inp, out, api_name="/text_search")
            with gr.Tab("表格"):
                g = gr.Dropdown(choices=["category", "region"], value="category")
                m = gr.Dropdown(choices=["revenue", "orders"], value="revenue")
                a = gr.Dropdown(choices=["sum", "avg"], value="sum")
                l = gr.Slider(1, 50, value=10, step=1)
                out = gr.Dataframe()
                btn = gr.Button("统计")
                def run_table(gb, mm, aa, ll):
                    res = table_stats({"group_by": gb, "metric": mm, "agg": aa, "limit": int(ll)})
                    return {"data": res["rows"], "headers": res["columns"]}
                btn.click(run_table, [g, m, a, l], out, api_name="/table_stats")
            with gr.Tab("折线"):
                metric = gr.Dropdown(choices=["revenue", "orders"], value="revenue")
                start = gr.Textbox(placeholder="YYYY-MM-DD")
                end = gr.Textbox(placeholder="YYYY-MM-DD")
                interval = gr.Dropdown(choices=["day", "week"], value="day")
                out = gr.LinePlot()
                btn = gr.Button("生成")
                def run_line(mm, ss, ee, ii):
                    res = line_series({"metric": mm, "start": ss, "end": ee, "interval": ii})
                    xs = res["x"]
                    ys = res["y"]
                    return [(xs, ys)]
                btn.click(run_line, [metric, start, end, interval], out, api_name="/line_series")
    return demo


def main():
    demo = build_interface()
    host = os.environ.get("GRADIO_HOST", "0.0.0.0")
    port = int(os.environ.get("GRADIO_PORT", "7860"))
    demo.launch(server_name=host, server_port=port)


if __name__ == "__main__":
    main()
