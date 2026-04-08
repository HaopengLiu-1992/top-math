#!/bin/bash
# Start local MLX server with Qwen3.5-9B-4bit
# Run from repo root: bash models/serve.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODEL_DIR="$SCRIPT_DIR/qwen3-9b-4bit"

if [ ! -d "$MODEL_DIR" ]; then
  echo "Model not found at $MODEL_DIR"
  echo "Download it first:"
  echo "  python -m mlx_lm.manage --download mlx-community/Qwen3.5-9B-MLX-4bit --local-dir models/qwen3-9b-4bit"
  exit 1
fi

echo "Starting MLX server with Qwen3.5-9B-4bit on port 8080..."
python -m mlx_lm server --model "$MODEL_DIR" --port 8080 --chat-template-args '{"enable_thinking":false}'
