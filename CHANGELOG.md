# Changelog

本文件记录 Agent Daily 的阶段演进。每个 Phase / 阶段完成后更新。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [0.1.0] - 2026-08-16

### Phase 0 — 项目初始化与接口冻结

**完成内容**
- 建立 `agent-daily` 项目骨架（pyproject / README / src/agent_daily）
- 冻结 8 模块接口：config / storage / model / prompt / agent / tools / output / jobs
- 实现 `agent-daily doctor` 环境自检（Python / 架构 / 配置 / mlxsvc 路径 / data 可写）
- 新增治理文件 CHANGELOG.md / ARCHITECTURE.md / DEVELOPMENT.md

**架构变化**
- 确立「Model 经 Provider、Output 经 Provider、Tool 经 Registry、Job 经 Workflow」分层原则
- 明确禁止：Agent 直接加载模型 / Job 直接调用外部 API / 任务之间内存共享

**测试结果**
- 单元测试 11/11 通过

### S1 — Storage 实现

**完成内容**
- `ArtifactStore`：save / load / exists，支持类型 json / markdown / text
- 路径 `data/processed/{YYYY-MM-DD}/`，日期按配置时区（默认 UTC+8）分区
- `Artifact` 含 name / type / path / created_at / metadata；元数据落盘 `.meta/` 侧车文件
- `StateStore`：`data/state/job_runs.jsonl` 追加运行记录（job / status / start_time / end_time / artifacts）

**架构变化**
- storage 模块签名定稿（Phase 0 为桩，S1 落地）

**测试结果**
- storage 测试 14/14 通过（读写 / 日期分区 / metadata / 追加 / 异常）
- 累计单元测试 25/25 通过

### S2 — Prompt 管理实现

**完成内容**
- `PromptManager`：load(name) / render(name, **variables)
- Prompt 对象含 name / version / description / template_content / variables
- Prompt 文件规范：Markdown + Front Matter（YAML 头部 + 正文模板）
- 严格变量校验：传入变量不足报错、模板引用未声明变量报错、Jinja2 StrictUndefined 兜底（禁止静默替换为空）
- 初始化模板 `prompts/summarize_repo.md`、`prompts/compose_report.md`
- 依赖新增 jinja2

**架构变化**
- prompt 模块签名定稿（Phase 0 为桩，S2 落地）；确立 Prompt 作为未来 UI 管理输出格式的数据载体

**测试结果**
- prompt 测试 9/9 通过（加载 / Front Matter 解析 / render / 缺变量 / 未声明变量 / 语法错误 / 真实模板）
- 累计单元测试 34/34 通过

### S3 — Model 执行层实现

**完成内容**
- 模型异常体系：ModelError / ModelLoadError / ModelTimeoutError / ModelProcessError / ModelAPIError
- `LocalMLXProvider.chat()`：messages → prompt 组装，subprocess 调 `uv run mlxsvc run --prompt`，支持 timeout
- `DeepSeekProvider.chat()`：httpx 调 OpenAI 兼容 /chat/completions，密钥读 secrets.env 的 DEEPSEEK_API_KEY
- `ModelManager.chat()`：固定 failover（primary 失败 → fallback），不做智能路由
- `create_model_manager()`：装配 primary=local / fallback=deepseek，DeepSeek 未配置仅本地运行
- 模型调用日志：provider / success / duration / error（logger `agent_daily.model`）
- 依赖新增 httpx

**架构变化**
- model 模块签名定稿（Phase 0 为桩，S3 落地）
- 落实「agent_daily 不 import mlx/mlx_lm、不直接加载模型、仅 subprocess 调 mlxsvc」

**测试结果**
- model 测试 13/13 通过（Mock 本地成功 / 本地失败降级 DeepSeek / 双失败 / 无 mlx_lm import 静态检查 / DeepSeek mock / timeout）
- 累计单元测试 47/47 通过

### S4 — GitHub Trending 工具实现

**完成内容**
- 目录 `tools/github_trending/`：models.py / source.py / official.py / mirror.py / parser.py / tool.py
- Source 与 Parser 严格分离：Source 只做 HTTP/URL/网络异常并返回原始响应；Parser 负责 HTML/JSON → Repo[]
- 数据源 official / mirror，地址全部来自 config.yaml（禁止硬编码），provider 默认 mirror
- `GithubSourceError` / `GithubParseError`：网络失败 / 解析失败 / 空结果一律显式抛异常，禁止空列表伪装成功
- httpx + timeout + 状态码检查；HTML 解析用 beautifulsoup4
- 配置新增 github.timeout_seconds 与 providers 的 format 字段

**架构变化**
- tools/github_trending 签名定稿（Phase 0 为桩，S4 落地）
- 确立 Source/Parser 分层：数据源变化不影响 Tool 层（未来镜像返回 JSON 只改 Parser）

**测试结果**
- github_trending 测试 18/18 通过（HTML/JSON 解析、Source/Parser 分离、provider 切换、URL 来自 config 静态检查、网络异常、解析异常）
- 累计单元测试 65/65 通过

### S5 — Output 输出层实现

**完成内容**
- `OutputError` / `IdempotencyRecord`（base.py）
- `LocalFileProvider`：title + content 写 Markdown 文件（离线/测试/fallback，同名覆盖天然幂等）
- `FeishuProvider`：tenant_access_token 获取 → 创建文档 → 写入内容块 → 返回 document_id
- 幂等机制：record_path 记录 key→document_id，同一天重复执行不重复创建文档（跨进程持久化）
- 失败显式抛 OutputError（缺密钥 / HTTP 错误 / code != 0 / 响应异常），禁止空成功
- 密钥来自 secrets.env（FEISHU_APP_ID / FEISHU_APP_SECRET），禁止硬编码

**架构变化**
- output 模块签名定稿（Phase 0 为桩，S5 落地）
- 确立「Job 不直连外部 API，经 OutputProvider」与输出幂等原则

**测试结果**
- output 测试 8/8 通过（LocalFile 写入 / Feishu mock token→建文档→写内容序列 / API 失败 / 缺密钥 / 幂等去重含跨实例）
- 累计单元测试 73/73 通过

### S6 — Workflow Agent 核心实现

**完成内容**
- `ExecutionContext.resolve()`：`${step_id.field}` 引用解析（字段/索引/属性路径），解析失败抛 ContextResolutionError
- `StepExecutor`：四类步骤 tool / model / artifact(load/save) / output
- `WorkflowAgent.run()`：顺序执行 workflow.steps，保存结果到上下文，返回 ExecutionContext
- 失败策略：任何 step 失败立即停止，记录 step_id/step_type/error，抛 StepExecutionError（禁止吞异常）
- execution trace：记录 step 开始/成功/失败（含 error），用于 debug
- 确定性执行：无自主规划 / 无循环 / 无自动创建步骤

**架构变化**
- agent 模块签名定稿（Phase 0 为桩，S6 落地）；WorkflowAgent 构造新增 artifacts 依赖
- 落实「Job 定义流程，Agent 只执行步骤」的分工

**测试结果**
- agent 测试 13/13 通过（顺序执行 / tool / model / output / artifact load-save / ${}解析 / 未知步骤类型 / 失败中断 / trace）
- 累计单元测试 86/86 通过

### S7 — Jobs 任务层实现（第一条业务闭环）

**完成内容**
- `JobRegistry`：加载 jobs/*.yaml → JobSpec（job/schedule/inputs/outputs/workflow.steps），非法 YAML / 缺字段 / 非法 step 类型明确报错
- `JobRunner`：加载 → 校验 inputs → 装配依赖 → WorkflowAgent → 校验 outputs → 记录 StateStore（成功/失败均记录，失败含 error）
- `build_agent_factory`：装配 ModelManager/PromptManager/ToolRegistry/OutputRegistry/ArtifactStore
- 两个任务定义：`github_trending.yaml`（采集→批量摘要→组织→存工件）、`feishu_report.yaml`（读工件→输出飞书，fallback LocalFile）
- model step 新增 batch 模式（逐项渲染 summarize_repo）、output step 新增 fallback、artifact step 的 date 支持 ${}
- CLI 新增 `agent-daily run <job_id>` + logging_util

**架构变化**
- jobs 模块签名定稿（Phase 0 为桩，S7 落地）
- 完成「launchd → Job → WorkflowAgent → Tool/Model/Output → Artifact」第一条完整闭环（数据源/模型可 mock）

**测试结果**
- jobs 测试 12/12 通过（YAML 加载 / 非法配置 / inputs 缺失 / outputs 契约 / Agent 调用 / State 成功+失败记录 / 真实定义 / 端到端三工件）
- 累计单元测试 98/98 通过
- CLI 冒烟：无 mirror 配置与缺输入工件均显式失败并记录状态

### S8 — Scheduler 调度实现（Phase 1 完成）

**完成内容**
- `scheduler.py`：schedule 解析（HH:MM → Hour/Minute，非法报错）、plist 生成（模板渲染）、install/uninstall/status
- `scheduler/templates/com.agent-daily.job.plist.tpl`：plist 模板（ProgramArguments=uv run agent-daily run，含 PATH/HOME/ThrottleInterval=300/Background/LowPriorityIO）
- `scheduler/install-jobs.sh` / `uninstall-jobs.sh`：从 jobs/*.yaml 自动生成 plist → launchctl load/unload
- CLI 新增 `agent-daily scheduler install/uninstall/status`
- doctor 新增 scheduler 检查（launchd 可用 / uv 可用 / plist 已生成 / launchd 日志可写）

**架构变化**
- 完成「launchd → Job → WorkflowAgent → Tool/Model/Output → Artifact → StateStore」第一条业务闭环
- launchd 仅负责调度，业务逻辑保持在 `agent-daily run <job_id>`，scheduler 不复制任何 Job/Workflow/Agent 逻辑

**测试结果**
- scheduler 测试 12/12 通过（schedule 转换 / label / ProgramArguments / WorkingDirectory / 日志路径 / 安全字段 / 非法 schedule / install-uninstall 生成删除）
- 累计单元测试 110/110 通过

**验收状态**
- 代码实现完成 ✓ / 自动测试完成 ✓ / 真实 macOS 权限验收（launchctl load）待用户本机执行

### Phase 1.5 — Feishu CLI 输出适配

**完成内容**
- `FeishuCLIProvider`（output/feishu_cli.py）：subprocess 调 `lark-cli markdown +create --content - --name "<title>.md"`，内容经 stdin 传入
- 失败显式抛 OutputError：命令缺失 / 非 0 退出 / 超时 / stdout 无有效结果（非 JSON / ok != true / 缺 file_token）
- `OutputRegistry` 新增 `set_default` + `get` 回退：provider 未注册时回退到 config 的 `output.default`
- config 新增 `output.feishu_cli.command` / `timeout_seconds`，`output.default` 默认 `feishu_cli`
- 保留 `output/feishu.py`（Open API Provider）不删除；registry 支持 local_file / feishu / feishu_cli
- 修复：恢复 S7 误删的 `agent-daily config` 子命令

**架构变化**
- 输出层新增第三种 Provider；不改 WorkflowAgent / Job YAML / ArtifactStore / Prompt，经 registry 默认解析让 `feishu_report` 的 `provider: feishu` 回退到 feishu_cli

**测试结果**
- feishu_cli 测试 10/10 通过（成功返回 file_token / stdin 内容 / title→name.md / 非0退出 / 超时 / 命令缺失 / 无有效结果 / ok=false / registry 默认回退）
- 累计单元测试 120/120 通过

---

## Phase 1 Complete

Phase 1（S1–S8 + Phase 1.5）完成，以下链路已验证：

- ✅ **local MLX inference** —— 本地 MLX 推理（subprocess 调 mlxsvc，不直接加载模型）
- ✅ **GitHub data collection** —— GitHub 热榜采集（Source Adapter 切换官方/镜像，URL 零硬编码）
- ✅ **workflow execution** —— Workflow Agent 顺序执行步骤（tool/model/artifact/output）
- ✅ **artifact pipeline** —— Artifact 落盘传递（跨任务唯一数据通道，日期分区）
- ✅ **launchd scheduling** —— launchd 定时任务（plist 由 jobs/*.yaml 自动生成）
- ✅ **Feishu CLI document delivery** —— lark-cli markdown +create 输出飞书文档

累计单元测试 120/120 通过。真实 macOS 定时任务装载（launchctl load）需用户本机执行。

---

## Phase 1.5 — Control Plane（Web UI 管理平台）

### Phase 1.5-S1-A — FastAPI 只读后端

**完成内容**
- `control/repo.py`：只读数据仓储（文件即真相），读 jobs / runs / artifacts / config / logs / scheduler / models
- `control/api.py`：FastAPI 只读后端，8 组端点
  - `/api/health` `/api/jobs` `/api/runs` `/api/artifacts` `/api/config` `/api/logs` `/api/scheduler/status` `/api/models`
- CLI 新增 `agent-daily serve [--host] [--port]`
- 依赖新增 fastapi / uvicorn
- secrets 只返回掩码（bool）；日志 tail 带路径穿越防护

**架构变化**
- 新增 Control Plane 层（只读），Runtime 零改动；只 import 只读/校验模块，不 import 执行模块
- 确立「文件即真相」：Control Plane 直接读 jobs/*.yaml、config.yaml、data/state、data/processed

**测试结果**
- control_api 测试 11/11 通过（8 端点 + 路径穿越防护 + 真实数据读取）
- 累计单元测试 131/131 通过
- serve 冒烟：`/api/health` `/api/jobs` `/api/models` 正确返回 v0.1.0 数据

### Phase 1.5-S1-B — 最小 Vue Dashboard（只读）

**完成内容**
- `frontend/`：Vue3 + Vite + TypeScript + Naive UI + Axios + vue-router
- 三个只读页面：Dashboard（系统状态/任务状态/最近运行）、Jobs（任务列表）、Artifacts（日期选择 + 工件列表 + 内容预览）
- 所有数据经 HTTP API（`/api/*`）获取；Vite dev 代理 `/api` → 127.0.0.1:8787
- FastAPI 挂载静态前端（`frontend/dist` 存在时），不改变任何 `/api` 端点

**架构变化**
- Control Plane 新增静态前端托管；Runtime 与 `/api` 端点零改动；无数据库、无认证、无编辑

**验收结果**
- `npm install` ✓ / `npm run build` ✓（dist 生成）
- `uv run agent-daily serve` 后：`/` 返回 index.html、`/assets/*` 静态资源 200、`/api/*` 正常
- 累计单元测试 131/131 通过（无回归）

### Phase 1.5-S2 — Control Plane 完整观察视图

**完成内容**
- 前端新增 Runs / Models / Scheduler / Logs / Config 五个页面，接通后端既有只读 API
- Runs 支持按任务筛选、分页和错误详情查看
- Models 展示 primary / fallback、启用状态和非敏感模型配置
- Scheduler 展示 launchd 的实际注册状态；Logs 支持文件选择与最近 200 行查看
- Config 展示合并后的生效配置，密钥仅显示“已配置/未配置”
- 侧边导航补齐八个观察入口，并优化窄屏内容区布局

**架构约束**
- UI 仍为只读观察层，不直接执行 Job、修改配置或加载/卸载 launchd
- 所有数据继续通过 `/api/*` 获取，保持“文件即真相”和 Runtime 零侵入

**验收结果**
- Vue/Vite 生产构建通过
- 后端单元测试 132/132 通过

### Phase 1.6 — 摘要与飞书快报质量修复

**完成内容**
- Qwen3 推理默认关闭 thinking，避免 `<think>` 内部推理进入摘要工件
- 收紧单项目 Prompt：一句话、禁止模板化开头、禁止复述语言与 Star、禁止杜撰
- 新增摘要标准化工具，清理思考标签、通用开头和重复元数据后再保存 summaries
- 报告改为确定性 Markdown 组装，逐项保留全部项目，不再由 0.6B 模型二次压缩长上下文
- 自动生成语言分布与最高关注度观察，Star 数统一千分位格式

**修复效果**
- report 从单条残缺内容恢复为完整 10 条项目
- summaries 中 `<think>` 与“该项目/本项目/这是一个”模板化开头均清零
- 模型调用从 11 次降至 10 次，真实运行耗时约 20 秒
