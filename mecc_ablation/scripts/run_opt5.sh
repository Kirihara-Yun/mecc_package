#!/bin/bash
cd /home/qinzy/mecc_package/e2e
rm -rf __pycache__
export TMPDIR=/data/tmp PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
echo "START opt5 $(date)"
python3 -u run_e2e.py --model mistralai/Mixtral-8x7B-Instruct-v0.1 \
  --state_path /data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61 \
  --store_root /data/mecc_store --hbm_budget 22 --cpu_budget 40 --alpha 1.0 \
  --max_new_tokens 8 --n_prompts 2 --policies ours --skip_ppl \
  --out /data/mecc_ablation/05_router_prefetch.json
echo "DONE opt5 $(date)"
