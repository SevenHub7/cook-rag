#!/usr/bin/env bash
# cook-rag 后端一键启动脚本
# 用法：先激活你的 Python 环境（conda activate xxx / source venv/bin/activate），再执行 ./run.sh
cd "$(dirname "$0")"
exec python3 -m uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}"
