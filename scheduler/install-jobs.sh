#!/usr/bin/env bash
# 安装 launchd 定时任务：从 jobs/*.yaml 生成 plist → launchctl load。
# 用法: bash scheduler/install-jobs.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

exec uv run agent-daily scheduler install
