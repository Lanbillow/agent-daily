# Agent Daily

运行在 macOS（Apple Silicon）上的个人 AI Agent 系统。

- **模型执行**：本地 MLX（经 `mlxsvc`，不依赖 LM Studio / Ollama）+ 远端 DeepSeek API（备用）
- **Agent**：第一阶段为 Workflow Agent（Job 定义流程，Agent 执行步骤）
- **工具**：GitHub 采集（Source Adapter 切换官方/镜像）、Web 搜索、网页抓取、飞书文档输出
- **自动任务**：UTC+8 每日 09:00 采集 GitHub 热榜并中文摘要、10:00 生成飞书快报

> **当前阶段：Phase 1 完成**（S1–S8 全部落地）。
> 已实现 Storage / Prompt / Model / Tool / Output / Workflow Agent / Jobs / Scheduler 八层，
> 完成「launchd → Job → WorkflowAgent → Tool/Model/Output → Artifact → StateStore」第一条业务闭环。
> 真实 macOS 定时任务安装（launchctl load）需用户在本机执行，见下方「调度（launchd）」。

---

## 前置要求

- **uv**：Python 环境与依赖管理（`uv sync`）。
- **mlxsvc**：本地 MLX 推理服务（`mlx-service/`，已独立实现，`uv run mlxsvc`）。
- **lark-cli**（飞书 CLI 输出，个人模式推荐）：
  1. 安装 `lark-cli`，确保在 `PATH` 中（`which lark-cli`）；
  2. 完成 OAuth 登录：`lark-cli auth login`；
  3. 验证：`printf '# hi' | lark-cli markdown +create --content - --name test.md` 能生成飞书文档。
  > 若不用飞书，可在 `config.yaml` 设 `output.default: local_file` 走本地文件输出。
- （可选）GitHub 镜像地址、DeepSeek API Key、飞书自建应用密钥（`secrets.env`）。

---

## 目录结构

```
agent-daily/
├── pyproject.toml              # 包 agent_daily + 入口 agent-daily
├── config/
│   ├── config.yaml.example     # 配置模板（复制为 config.yaml）
│   └── secrets.env.example     # 密钥模板（复制为 secrets.env）
├── prompts/                    # Prompt 模板（Markdown，未来 UI 编辑对象）
├── jobs/                       # 任务定义（YAML，未来 UI 增删对象）
├── scheduler/                  # launchd 调度（S8）
├── src/agent_daily/
│   ├── cli.py                  # 入口（当前仅 doctor）
│   ├── doctor.py               # 环境自检
│   ├── config/                 # schema + loader
│   ├── model/                  # ModelProvider / Local / DeepSeek / Manager(failover)
│   ├── prompt/                 # PromptManager
│   ├── agent/                  # WorkflowAgent / steps / context / memory(接口)
│   ├── tools/                  # Tool 协议 + 注册表 + github_trending 等
│   ├── output/                 # OutputProvider / LocalFile / Feishu / Telegram(预留)
│   ├── jobs/                   # JobRegistry / JobRunner
│   └── storage/                # ArtifactStore / StateStore
├── tests/
└── data/                       # 运行时产物（gitignore）
```

## 模块接口（已冻结并实现）

| 层 | 核心接口 | 状态 |
|---|---|---|
| model | `ModelProvider.chat(messages) -> str`；`ModelManager` 仅 failover | 已实现 |
| prompt | `PromptManager.load/render(name)` | 已实现 |
| agent | `WorkflowAgent.run(task_input) -> ExecutionContext`；`Memory`/`NullMemory` | 已实现 |
| tools | `Tool.run(args) -> ToolResult`；`ToolRegistry` | 已实现 |
| output | `OutputProvider.write(title, content)`；`OutputRegistry` | 已实现 |
| jobs | `JobSpec` / `JobRegistry` / `JobRunner` | 已实现 |
| storage | `ArtifactSpec` / `ArtifactStore` / `StateStore` | 已实现 |
| scheduler | `install_jobs` / `uninstall_jobs` / `status` | 已实现 |

## 启动方式

```bash
cd "/Users/lanze/Desktop/Agent daily/agent-daily"

# 安装依赖（首次）
uv sync

# 环境自检
uv run agent-daily doctor

# 生成配置（可选，缺失时使用默认值）
cp config/config.yaml.example config/config.yaml
cp config/secrets.env.example secrets.env 2>/dev/null || cp config/secrets.env.example config/secrets.env
```

`doctor` 检查：Python 版本、Apple Silicon 架构、配置文件/模板/密钥存在性、
mlxsvc 路径、data 目录可写性，以及 launchd 调度状态。全部通过退出码 0，否则 1。

### 执行单个任务

```bash
uv run agent-daily run github_trending     # 采集+摘要+生成快报（3 个工件）
uv run agent-daily run feishu_report       # 读报告 → 输出飞书/本地文件
```

## 调度（launchd）

```bash
# 安装定时任务（从 jobs/*.yaml 自动生成 plist 并 launchctl load）
bash scheduler/install-jobs.sh

# 查看任务注册状态
uv run agent-daily scheduler status

# 手动触发一次（调试）
launchctl start com.agent-daily.github-trending

# 卸载
bash scheduler/uninstall-jobs.sh
```

> 安装/卸载会写入 `~/Library/LaunchAgents` 并调用 `launchctl`，需在本机 macOS 环境执行。

---

## 真实运行方式（端到端）

```bash
cd "/Users/lanze/Desktop/Agent daily/agent-daily"

# 0. 安装依赖
uv sync

# 1. 配置（复制模板后按需修改）
cp config/config.yaml.example config/config.yaml
cp config/secrets.env.example config/secrets.env
#   config.yaml 必改：github.providers.mirror.base_url = "你的镜像地址"
#   output.default 已默认 feishu_cli（经 lark-cli）

# 2. lark-cli 前置（飞书输出）
lark-cli auth login        # 已完成 OAuth 则跳过

# 3. 自检
uv run agent-daily doctor

# 4. 手动跑通两条任务
uv run agent-daily run github_trending    # 产出 trending.json / summaries.json / report.md
uv run agent-daily run feishu_report      # 读 report → 飞书生成「YYYY-MM-DD热点快报.md」

# 5. 安装定时任务（无人值守，09:00 / 10:00）
bash scheduler/install-jobs.sh
uv run agent-daily scheduler status

# 6. 手动触发验证
launchctl start com.agent-daily.github-trending
cat data/state/job_runs.jsonl                # 应出现 success 记录
ls data/processed/$(date +%Y-%m-%d)/         # 3 个工件
```

---

## 路线图

| 阶段 | 内容 | 状态 |
|---|---|---|
| S1 | storage（Artifact 读写 + 运行历史） | ✓ 完成 |
| S2 | PromptManager（加载 + Jinja2 渲染） | ✓ 完成 |
| S3 | Model（LocalMLX subprocess + DeepSeek + failover） | ✓ 完成 |
| S4 | github_trending（Source Adapter：official/mirror） | ✓ 完成 |
| S5 | Output（LocalFile + Feishu Open API + 幂等） | ✓ 完成 |
| S6 | WorkflowAgent（步骤执行 + 上下文回填） | ✓ 完成 |
| S7 | Jobs（registry + runner + 两个 job YAML） | ✓ 完成 |
| S8 | Scheduler（launchd 定时 + plist 生成） | ✓ 完成 |
