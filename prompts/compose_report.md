---
name: compose_report
version: 1
description: 每日热点快报正文组织
variables:
  - date
  - summaries
---

你是内容编辑。请根据下面的项目摘要，组织一篇「{{ date }} 热点快报」正文。

项目摘要：
{% for s in summaries %}
- {{ s.name }}（{{ s.language }}，{{ s.stars }} ⭐）：{{ s.summary }}
{% endfor %}

要求：
- 使用 Markdown，按项目分条目列出
- 每条包含：项目名、一句话中文描述、主要语言、Star 数
- 结尾附一句今日整体观察

直接输出 Markdown 正文（不要重复一级标题）：
