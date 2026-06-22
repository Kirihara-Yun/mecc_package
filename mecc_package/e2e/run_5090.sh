#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
# run_5090.sh —— 5090 一键: 环境检查 → 下载模型 → profiling → 编译 → 四策略端到端主表
# 用法:
#   bash run_5090.sh smoke        # 仅本机逻辑自检 (不下载, 秒级)
#   bash run_5090.sh full         # 完整真实 Mixtral 端到端 (需下载 ~90GB)
# 环境变量 (可覆盖):
#   MODEL       默认 mistralai/Mixtral-8x7B-Instruct-v0.1
#   STATE_PATH  模型 snapshot 目录 (留空则自动下载到 HF cache)
#   STORE_ROOT  SSD expert 冷存目录 (建议放高速 NVMe, 需 ~90GB 空闲)
#   HBM_BUDGET  留给 expert 的 HBM(GB), 默认 22 (32GB - trunk/KV ~10GB)
#   CPU_BUDGET  留给 expert 的内存(GB), 默认 40
# ════════════════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")"

MODE="${1:-full}"
MODEL="${MODEL:-mistralai/Mixtral-8x7B-Instruct-v0.1}"
STORE_ROOT="${STORE_ROOT:-/tmp/mecc_store}"
HBM_BUDGET="${HBM_BUDGET:-22}"
CPU_BUDGET="${CPU_BUDGET:-40}"
PY="${PY:-python3}"

echo "=================================================================="
echo " MECC End-to-End @ 5090   mode=$MODE"
echo "=================================================================="

if [ "$MODE" = "smoke" ]; then
  $PY run_e2e.py --smoke --n_prompts 4 --store_root "${STORE_ROOT}_smoke" --out smoke_table.json
  echo "[smoke] OK → smoke_table.json"
  exit 0
fi

# ---- 0. 环境检查 ----
$PY - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    p = torch.cuda.get_device_properties(0)
    print(f"GPU: {p.name}  {p.total_memory/1e9:.0f}GB  sm_{p.major}{p.minor}")
PY

# ---- 1. 防盘满 + 确认 /tmp/store 落在真盘 (非 tmpfs) ----
echo "[disk] store_root=$STORE_ROOT"; df -h "$(dirname "$STORE_ROOT")" || true

# ---- 2. (可选) 真实 profiling 估 α —— 用小 MoE 快速拟合, 写 real_alpha.json ----
#   若已有真实 per-layer 访问统计可传 --profile; 这里默认用 α=1.0 (Mixtral 实测偏均匀)
ALPHA="${ALPHA:-1.0}"

# ---- 3+4. 编译 + 四策略端到端 (expert 首跑会流式物化到 SSD, 之后复用) ----
EXTRA=""
[ -n "$STATE_PATH" ] && EXTRA="--state_path $STATE_PATH"

$PY run_e2e.py \
  --model "$MODEL" $EXTRA \
  --store_root "$STORE_ROOT" \
  --hbm_budget "$HBM_BUDGET" --cpu_budget "$CPU_BUDGET" \
  --alpha "$ALPHA" \
  --prompt_len 64 --max_new_tokens 64 --n_prompts 8 \
  --ppl_tokens 1024 \
  --out main_table_5090.json

echo "=================================================================="
echo " DONE → main_table_5090.json  (可直接进 DAC 主表)"
echo "=================================================================="
