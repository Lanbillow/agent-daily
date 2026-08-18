#!/usr/bin/env bash
# 卸载 launchd 定时任务：launchctl unload + 删除 plist。
# 用法: bash scheduler/uninstall-jobs.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

exec uv run agent-daily scheduler uninstall
