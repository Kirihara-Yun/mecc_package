#!/bin/bash
# P2 预算/成本敏感性 (E10/E14) 串行 driver。
# 扫描 cpu_budget ∈ {20,30,60}（cpu=40 已由 P1 复用），固定 hbm=50，5 策略各独立 run。
# 每个 run 等待 complete/failed 后自动推进下一个；结果落 results/runs/，进度落 p2_driver.log。
set -u

ROOT=/home/qinzy/mecc_package
STATE=/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61
CONFIG="$ROOT/mecc_package/e2e/configs/l2_mixtral_repro.json"
LAUNCHER="python3 $ROOT/mecc_package/scripts/experiment_launcher.py"
LOGFILE="$ROOT/mecc_package/results/reports/p2_driver.log"
RUNS_ROOT="$ROOT/mecc_package/results/runs"

log() { echo "[$(date '+%F %T')] $*" >> "$LOGFILE"; }

# 待跑队列：cpu policy（cpu=20 的 ours 已完成，故从 swapmoe 开始）
QUEUE="20 swapmoe
20 fiddler
20 naive
20 flashmoe_rf_adaptation
30 ours
30 swapmoe
30 fiddler
30 naive
30 flashmoe_rf_adaptation
60 ours
60 swapmoe
60 fiddler
60 naive
60 flashmoe_rf_adaptation"

FAILED=0
TOTAL=0

while read -r cpu policy; do
  [ -z "$cpu" ] && continue
  TOTAL=$((TOTAL+1))
  run_id="a100-p2-cpu${cpu}-${policy}-20261104"
  log "START $run_id cpu=$cpu policy=$policy"
  $LAUNCHER run "$run_id" --config "$CONFIG" --state-path "$STATE" --gpu 0 \
    --policies "$policy" --n-prompts 4 --cpu-budget "$cpu" >> "$LOGFILE" 2>&1
  while true; do
    phase=$(python3 -c "import json,sys;print(json.load(open('$RUNS_ROOT/$run_id/status.json')).get('phase',''))" 2>/dev/null || echo "")
    if [ "$phase" = "complete" ]; then log "COMPLETE $run_id"; break; fi
    if [ "$phase" = "failed" ]; then log "FAILED $run_id"; FAILED=$((FAILED+1)); break; fi
    sleep 120
  done
done <<< "$QUEUE"

log "ALL_DONE total=$TOTAL failed=$FAILED"
