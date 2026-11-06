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

TOTAL=0
# fiddler 在 cpu30 实测 2h34m（>2h），cpu60 的 fiddler 会更慢；观察上限放宽到 4h 避免误杀。
MAX_WALL_SECONDS=14400

while read -r cpu policy; do
  [ -z "$cpu" ] && continue
  TOTAL=$((TOTAL+1))
  run_id="a100-p2-cpu${cpu}-${policy}-20261104"
  run_dir="$RUNS_ROOT/$run_id"
  unit="mecc-exp-${run_id}.service"
  if [ -d "$run_dir" ]; then
    phase=$(python3 -c "import json;print(json.load(open('$run_dir/status.json')).get('phase',''))" 2>/dev/null || echo "")
    if [ "$phase" = "complete" ] && [ -s "$run_dir/result.json" ]; then
      log "SKIP_COMPLETE $run_id"
      continue
    fi
    state=$(systemctl --user is-active "$unit" 2>/dev/null || true)
    if [ "$state" != "active" ] && [ "$state" != "activating" ]; then
      log "STOP_INCOMPLETE $run_id phase=$phase unit=inactive"
      exit 1
    fi
    log "RESUME_MONITOR $run_id phase=$phase"
  else
    log "START $run_id cpu=$cpu policy=$policy"
    launch_ok=0
    for attempt in 1 2 3 4 5; do
      if $LAUNCHER run "$run_id" --config "$CONFIG" --state-path "$STATE" --gpu 0 \
        --policies "$policy" --n-prompts 4 --cpu-budget "$cpu" >> "$LOGFILE" 2>&1; then
        launch_ok=1
        break
      fi
      # 前一 unit 可能尚未完全 deactivate，launcher 会以「active MECC job」拒绝；等待后重试。
      log "LAUNCH_RETRY $run_id attempt=$attempt"
      sleep 30
    done
    if [ "$launch_ok" -ne 1 ]; then
      log "STOP_LAUNCH_FAILED $run_id"
      exit 1
    fi
  fi
  started_at=$(date +%s)
  while true; do
    phase=$(python3 -c "import json;print(json.load(open('$run_dir/status.json')).get('phase',''))" 2>/dev/null || echo "")
    if [ "$phase" = "complete" ] && [ -s "$run_dir/result.json" ]; then
      log "COMPLETE $run_id"
      break
    fi
    if [ "$phase" = "failed" ]; then
      log "STOP_FAILED $run_id"
      exit 1
    fi
    state=$(systemctl --user is-active "$unit" 2>/dev/null || true)
    if [ "$state" != "active" ] && [ "$state" != "activating" ]; then
      log "STOP_UNIT_INACTIVE $run_id phase=$phase state=$state"
      exit 1
    fi
    if [ $(( $(date +%s) - started_at )) -ge "$MAX_WALL_SECONDS" ]; then
      log "STOP_TIMEOUT $run_id phase=$phase elapsed_s=$MAX_WALL_SECONDS"
      exit 1
    fi
    sleep 30
  done
done <<< "$QUEUE"

log "ALL_DONE total=$TOTAL failed=0"
