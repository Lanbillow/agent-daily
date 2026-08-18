# Agent Daily 架构（冻结）

本文档记录当前冻结的架构。**修改架构必须同步更新本文档。**

## 1. 分层结构

```
scheduler ─▶ jobs ─▶ agent(Workflow) ─┬─▶ model(Provider → mlxsvc)
                                      ├─▶ tools(Registry)
                                      └─▶ output(Provider → 飞书API)
jobs/agent ─▶ storage(artifacts/state)
所有层 ─▶ config · prompt · logging
```

依赖方向单向向下，上层依赖下层，禁止反向。

## 2. 模块职责

| 层 | 职责 | 不做 |
|---|---|---|
| scheduler | launchd 定时触发 `agent-daily run <job>` | 不含业务 |
| jobs | 加载任务定义 + 校验 Artifact I/O 契约 + 驱动 Agent | 不跨任务直连 |
| agent | Workflow Agent：按 Job 定义的步骤顺序执行，管理上下文、组织结果 | 不做自主 ReAct（Phase 1） |
| model | `ModelProvider` 统一接口 + LocalMLX / DeepSeek + `ModelManager`(仅 failover) | 不做复杂路由 |
| tools | `Tool` 统一接口 + `ToolRegistry` 注册 | 不硬编码外部地址 |
| output | `OutputProvider` 统一接口 + FeishuCLI(推荐个人) / Feishu(Open API) / LocalFile / Telegram(预留) | 不做硬编码工具 |
| storage | Artifact 工件读写 + 运行历史 | — |
| prompt | `PromptManager` 按名加载渲染 `prompts/*.md` | — |

## 3. 数据流（两条每日任务）

```
09:00 github_trending:
  github_trending 工具 ─▶ trending.json   (Artifact)
  模型中文摘要        ─▶ summaries.json   (Artifact)
  模型组织报告        ─▶ report.md        (Artifact)

10:00 feishu_report:
  读 report.md (Artifact) ─▶ output(feishu_cli) ─▶ 飞书文档
```

## 4. Artifact 设计原则

- **任务间唯一数据通道**：禁止任务之间直接内存调用，一切跨任务数据经 `storage/artifacts` 落盘传递。
- **命名工件**：每个 Artifact 含 name / type / path / created_at / metadata。
- **日期分区**：路径 `data/processed/{YYYY-MM-DD}/`，按 UTC+8 分区。
- **类型化序列化**：json / markdown / text，由 type 决定序列化与扩展名。
- **元数据落盘**：元数据写入 `.meta/` 侧车文件，保证跨进程（launchd 独立进程）可读。

## 5. ModelProvider 设计原则

- **统一接口**：`chat(messages) -> str`，上层不感知引擎。
- **Agent Daily 不直接加载 MLX 模型**：本地经 `LocalMLXProvider` 用 subprocess 调 mlxsvc。
- **本地默认、远端备用**：`ModelManager` 仅做 failover（primary 失败切 fallback），不做复杂度路由。

## 6. OutputProvider 设计原则

- **统一抽象**：`write(title, content) -> 标识`。
- **飞书不是硬编码工具**：Job 不直接调飞书 API，必须经 Agent → OutputProvider → 具体 Provider。
- **可插拔**：
  - `FeishuCLIProvider`（**推荐个人模式**）：经 `lark-cli markdown +create` 把 Markdown 直接创建为飞书文档，基于用户 OAuth 登录，无需 app_id/app_secret。
  - `FeishuProvider`（Open API）：飞书自建应用 app_id/app_secret，适合自动化/机器人身份。
  - `LocalFileProvider`（离线/测试/fallback）、`TelegramProvider`（预留）。
- **默认解析**：`OutputRegistry` 未命中显式 provider 时回退到 `output.default`（个人模式默认 `feishu_cli`），故 Job YAML 无需硬编码 provider 实现。

## 7. 明确禁止

1. **Agent 直接加载模型**（必须经 ModelProvider）。
2. **Job 直接调用外部 API**（飞书/GitHub/DeepSeek 等，必须经 Provider/Tool）。
3. **任务之间内存共享**（必须经 storage/artifacts）。
