# 项目开发与改造指南（Gradio → MCP 对话式）

## 目标与概述

- 将传统 Gradio WebUI 的“显式参数输入 → 函数调用 → 返回结果”流程改造成“对话式 → MCP 语义插槽填充 → 参数校验 → 通过 Gradio Client 调用绑定函数 → 返回结果”的闭环。
- 保留原始非对话式应用以便横向对比；提供统一前端同时包含原始与对话式两个使用入口。
- 全流程仅使用本地 `ollama` 模型进行推理，离线可用。

## 架构分层

- server：数据与业务函数
  - 数据源与样例 `server/data_store.py`
  - 三类工具与 API 逻辑 `server/functions.py`
  - 原始非对话式 WebUI `server/gradio_app.py`
  - 统一前端（原始 + 对话式）`server/unified_app.py`
- mcp：对话式工具规划
  - 引擎与工具注册 `mcp/engine.py:16`
- clients：桥接客户端
  - Gradio Client 桥接 `clients/gradio_bridge.py:4`
- chat：命令行对话入口
  - CLI 演示 `chat/cli.py:36`

## 关键代码参考

- 工具注册表与参数模式：`server/functions.py:78`
  - 文本检索 `server/functions.py:7`
  - 表格统计 `server/functions.py:22`
  - 时间序列折线 `server/functions.py:48`
- MCP 引擎：`mcp/engine.py:16`
  - 系统提示拼接工具与响应 JSON Schema：`mcp/engine.py:25`
  - 本地 `ollama` Chat API 调用：`mcp/engine.py:52`
  - 参数校验与默认补全：`mcp/engine.py:77`
  - Gradio Client 调用桥接与回退：`mcp/engine.py:118`
- 原始 WebUI：`server/gradio_app.py:5`
- 统一前端：`server/unified_app.py:1`

## 快速开始

### 安装依赖

- Python 3.9+
- 本地 `ollama` 与模型（示例使用 `qwen3:8b`）
- 安装 Gradio 与 Gradio Client：

```bash
pip install gradio gradio_client
```

### 启动原始非对话式 WebUI

```bash
python -c "from server.gradio_app import main; main()"
# 默认端口 7860（可通过环境变量覆盖）
```

环境变量：

- `GRADIO_HOST` 默认 `0.0.0.0`
- `GRADIO_PORT` 默认 `7860`

### 启动统一前端（原始 + 对话式）

```bash
python -c "from server.unified_app import main; main()"
```

### 命令行对话演示（离线）

```bash
python chat/cli.py
```

可选环境变量：

- `MCP_MODEL` 设置对话模型（默认 `qwen3:8b`）
- `USE_GRADIO_CLIENT=1` 通过 Gradio Client 调用已绑定 API（默认走本地 handler）

## 统一前端说明

- Tab “原始应用”复刻传统表单：
  - 文本查询 API `/text_search` 在 `server/gradio_app.py:14` 与 `server/unified_app.py` 同步暴露
  - 表格统计 API `/table_stats` 在 `server/gradio_app.py:25`
  - 折线生成 API `/line_series` 在 `server/gradio_app.py:38`
- Tab “对话式应用”提供聊天 + 结构化输出：
  - 聊天消息经 MCP 规划，填充参数，并通过 Gradio Client 触发对应 API（如 `/table_stats`）
  - 根据返回类型渲染到 `文本输出`、`表格输出` 或 `折线输出`

## 将传统 Gradio 改写为对话式的步骤

1. 梳理功能与参数
   - 为每个函数定义工具名、描述与参数 JSON Schema（类型、默认值、必填字段）
   - 示例：见 `server/functions.py:78`
2. 构建 MCP 引擎
   - 在系统提示中发布“工具清单 + 响应 JSON Schema”，约束模型仅返回 JSON（`mcp/engine.py:25`）
   - 使用 `ollama` 本地推理得到 `{tool, arguments}`（`mcp/engine.py:52`）
   - 执行前做参数校验与类型补全（`mcp/engine.py:77`）
3. 绑定执行路径
   - 推荐通过 Gradio Client 调用命名 API（`mcp/engine.py:118` → `clients/gradio_bridge.py:4`）
   - 在 WebUI 中为每个功能暴露 `api_name` 以便可远程调用（`server/gradio_app.py:14,25,38`）
4. 统一前端集成
   - 原始 Tab：保留原有控件与点击事件
   - 对话式 Tab：引入 `Chatbot` 与输入框，调用 MCP 并渲染结构化结果（`server/unified_app.py:22`）
5. 验证与对比
   - 在原始 Tab 手动选择参数对比结果
   - 在对话式 Tab 用自然语言触发同一功能，比较体验与可解释性

## 设计原则与使用规范

- 工具原子化：一个工具只做一件清晰的事，便于模型选择
- 语义稳健：参数模式明确，默认值与类型转换要健壮（`mcp/engine.py:77`）
- 响应统一：输出类型采用 `{type, ...}` 统一封装，利于前端多模态渲染
- 本地优先：所有推理走本地 `ollama`，避免外部依赖
- 可回退：Gradio Client 不可用时回退到本地 handler（`mcp/engine.py:118`）
- API 可寻址：为每个功能绑定 `api_name`，确保客户端可调用（`server/gradio_app.py:14,25,38`）

## 常见问题

- 模型未返回纯 JSON
  - 引擎自动二次提示“Return only JSON”并重试（`mcp/engine.py:104`）
- 参数不匹配或缺失
  - 引擎做类型转换与默认补全，确保可执行（`mcp/engine.py:77`）
- Gradio Client 调用失败
  - 回退本地 handler（`mcp/engine.py:118`），或确认端口与 `api_name` 正确

## 扩展方向

- 增加图表类型与交互（柱状图、饼图、地图）
- 引入更严格的 Schema 校验（如 `jsonschema` 或 `pydantic`）
- 会话记忆与上下文复用（将历史注入 MCP 的系统提示）
- 权限控制与审计日志（记录工具选择与参数）

