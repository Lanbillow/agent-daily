# Agent Daily 开发规范

长期维护基础。所有贡献/改动必须遵守。

## 1. 代码规范

- **不破坏已冻结接口**：`ARCHITECTURE.md` 中冻结的接口签名不得随意更改；确需变更须先改文档再改代码。
- **新功能优先通过 Provider / Tool 扩展**：新增能力优先实现为新的 Provider 或 Tool，而非在核心模块里加分支。
- **修改架构必须更新文档**：改 ARCHITECTURE.md，并在 CHANGELOG.md 记录。
- **接口与实现分离**：每个模块先定接口（Protocol / dataclass），再实现。
- **先测试后合入**：新功能必须附带单元测试；测试不依赖网络 / 真实模型（可用 mock）。

## 2. 架构规范（硬性约定）

- **Model 通过 Provider**：所有模型调用经 `ModelProvider`，禁止直接 import mlx_lm / 直接调模型 API。
- **Output 通过 Provider**：所有输出经 `OutputProvider`，禁止 Job 直连飞书等外部 API。
- **Tool 通过 Registry**：工具必须实现 `Tool` 协议并注册到 `ToolRegistry`，禁止硬编码调用。
- **Job 通过 Workflow 定义**：任务流程写在 `jobs/*.yaml` 的 `workflow.steps`，由 WorkflowAgent 执行，禁止在 runner 里写死流程。

## 3. 目录约定

- `src/agent_daily/`：代码（模块接口 + 实现）。
- `prompts/`：Prompt 模板（Markdown，输出格式由模板控制）。
- `jobs/`：任务定义（YAML，数据非代码）。
- `config/`：`config.yaml.example` / `secrets.env.example`（真实配置与密钥不入库）。
- `data/`：运行时产物（gitignore）。

## 4. 阶段纪律

- 每个 Phase / 阶段完成后更新 CHANGELOG.md（完成内容 / 架构变化 / 测试结果）。
- 不提前实现未进入当前阶段的功能。
