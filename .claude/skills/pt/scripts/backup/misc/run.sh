#!/bin/bash

# 激活虛擬環境並運行腳本
# Activate virtual environment and run script

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"

# 檢查 venv 是否存在
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ 虛擬環境不存在，正在創建..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install -r "$SCRIPT_DIR/requirements.txt"
else
    echo "✅ 激活虛擬環境..."
    source "$VENV_DIR/bin/activate"
fi

# 運行腳本
echo "🚀 運行腳本..."
cd "$SCRIPT_DIR/scripts"
python "$@"