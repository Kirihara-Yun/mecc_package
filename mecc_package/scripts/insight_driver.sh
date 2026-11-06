#!/bin/bash
# E05–E08 动机三连（fig02）串行 driver。
# 固定 HBM=50 / CPU=40（G0_CONTRACT 冻结配置）、64 token / 8 prompts、--uniform。
# 三组 Insight 各独立 run，串行推进；进度落 insight_driver.log。
#   E05 (Insight I)   初始放置 per_layer / global / avg   —— 需 mixtral profile
#   E06 (Insight II)  更新规则 independent（joint=ours / fixed_cpu=swapmoe 已在主对比）
#   E07/E08 (Motivation III) 任务切换 a_b / b_a / a_a（none 已在主对比 ours）
set -u

ROOT=/home/qinzy/mecc_package
STATE=/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61
CONFIG="$ROOT/mecc_package/e2e/configs/l2_mixtral_main.json"
PROFILE="$ROOT/mecc_package/results/raw/mixtral_profile_20261105.json"
LAUNCHER="python3 $ROOT/mecc_package/scripts/experiment_launcher.py"
LOGFILE="$ROOT/mecc_package/results/reports/insight_driver.log"
RUNS_ROOT="$ROOT/mecc_package/results/runs"

log() { echo "[$(date '+%F %T')] $*" >> "$LOGFILE"; }

# QUEUE 每行 "run_id|extra launcher args"（| 分隔，extra 内可含空格由 bash 分词）
QUEUE="a100-e06-independent-20261105|--uniform --update-rule independent
a100-e05-per_layer-20261105|--policies ours --uniform --profile $PROFILE --init-plan per_layer
a100-e05-global-20261105|--policies ours --uniform --profile $PROFILE --init-plan global
a100-e05-avg-20261105|--policies ours --uniform --profile $PROFILE --init-plan avg
a100-e07-a_b-20261105|--policies ours --uniform --task-seq a_b
a100-e08-b_a-20261105|--policies ours --uniform --task-seq b_a
a100-e08-a_a-20261105|--policies ours --uniform --task-seq a_a"

MAX_WALL_SECONDS=14400

while IFS='|' read -r run_id extra; do
  [ -z "$run_id" ] && continue
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
    log "START $run_id extra=$extra"
    launch_ok=0
    for attempt in 1 2 3 4 5; do
      if $LAUNCHER run "$run_id" --config "$CONFIG" --state-path "$STATE" --gpu 0 \
        --hbm-budget 50 --cpu-budget 40 $extra >> "$LOGFILE" 2>&1; then
        launch_ok=1
        break
      fi
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

log "ALL_DONE total=$(echo "$QUEUE" | grep -c .) failed=0"
