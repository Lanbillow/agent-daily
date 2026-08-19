---
name: summarize_repo
version: 2
description: 单个 GitHub 项目的简短中文摘要
variables:
  - repo_name
  - description
  - language
  - stars
---

你是技术内容编辑。请把下面的 GitHub 项目写成一句自然、具体的中文摘要。

- 项目名：{{ repo_name }}
- 描述：{{ description }}
- 语言：{{ language }}
- Star 数：{{ stars }}

严格要求：
- 只输出最终摘要，不展示思考过程，不使用 `<think>` 标签
- 25-60 个中文字符，最多一句，不写标题
- 直接说“做什么、解决什么问题”，保留描述中的关键技术或数量
- 不要以“该项目”“本项目”“这是一个”“旨在”“适用于”开头
- 不复述项目名、语言、Star 数，不杜撰描述中没有的功能
- 只依据当前项目的描述；描述很短时宁可忠实简短，不补猜测出来的功能、用户或性能优势

最终摘要：
