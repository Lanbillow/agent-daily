---
name: summarize_repo
version: 1
description: 单个 GitHub 项目的简短中文摘要
variables:
  - repo_name
  - description
  - language
  - stars
---

你是技术内容编辑。请用 1-2 句中文概括下面这个 GitHub 项目的功能与用途，突出其核心价值，不要逐句翻译描述。

- 项目名：{{ repo_name }}
- 描述：{{ description }}
- 语言：{{ language }}
- Star 数：{{ stars }}

直接输出中文摘要（不要多余前缀或标题）：
