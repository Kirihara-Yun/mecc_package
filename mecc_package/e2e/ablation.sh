#!/bin/bash
# MECC Ablation: 逐优化 → Mixtral E2E 消融对比
# 每次只改一个方法, 改完立刻跑真实 Mixtral E2E 记录性能
set -e
export TMPDIR=/data/tmp
STORE=/data/mecc_store
STATE=/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61
RESULT_DIR=/data/mecc_ablation
ROOT=/home/qinzy/mecc_package
mkdir -p $RESULT_DIR

run_e2e() {
    local label=$1
    echo "========================================================"
    echo "  RUNNING: $label  ($(date +%H:%M:%S))"
    echo "========================================================"
    cd $ROOT/e2e
    rm -rf __pycache__
    TMPDIR=/data/tmp python3 run_e2e.py \
        --model mistralai/Mixtral-8x7B-Instruct-v0.1 \
        --state_path "$STATE" \
        --store_root "$STORE" \
        --hbm_budget 22 --cpu_budget 40 --alpha 1.0 \
        --max_new_tokens 8 --n_prompts 2 \
        --policies ours --skip_ppl \
        --out "$RESULT_DIR/${label}.json" 2>&1 | tee "$RESULT_DIR/${label}.log"
    # 记录
    python3 -c "
import json
with open('$RESULT_DIR/${label}.json') as f:
    r = json.load(f)['results']['ours']
print(f'[{label}] TTFT={r[\"ttft_ms\"]}ms  TPOT={r[\"tpot_ms\"]}ms  tok/s={r[\"tokens_per_s\"]}')
" >> "$RESULT_DIR/${label}.log"
}

# ────────────────────────────────────────────
# Step 0: Baseline (clean code)
# ────────────────────────────────────────────
cd $ROOT
git checkout master -- compile.py compiler.py concurrent_tiered_cache.py mecc_framework/ mecc_framework/cache/engine.py 2>/dev/null || true
rm -rf __pycache__ e2e/__pycache__
run_e2e "00_baseline"

# ────────────────────────────────────────────
# Opt 1: _evict_hbm_if_needed 零拷贝淘汰
#   问题: 淘汰时执行 ev_ws.to("cpu") 做昂贵的 D2H 拷贝
#   优化: 在 warmup/_access_ours 中同时保留 CPU 镜像,
#        淘汰时直接复用镜像 (零拷贝)
#   修改: mecc_framework/cache/engine.py
# ────────────────────────────────────────────
cd $ROOT
ENGINE=mecc_framework/cache/engine.py

# 1a. warmup: hbm 存储改为 (gpu_ws, cpu_ws) 对
sed -i 's/self\.hbm\[uid\] = ws\.to(self\.device)/ws_cpu = ws.clone(); self.hbm[uid] = (ws.to(self.device), ws_cpu)/' $ENGINE

# 1b. _access_ours: hbm[uid] = g 改为 hbm[uid] = (g, ws_cpu)
#     注意：这里 ws_cpu 在 SSD miss 分支也已被定义
python3 << 'PYEOF'
import re
path = 'mecc_framework/cache/engine.py'
with open(path) as f: src = f.read()
# _access_ours 中最后的 self.hbm[uid] = g
src = src.replace(
    '        self.hbm[uid] = g\n        self.hbm.move_to_end(uid)\n        self._evict_hbm_if_needed(spill_to_cpu=True)',
    '        self.hbm[uid] = (g, ws_cpu)\n        self.hbm.move_to_end(uid)\n        self._evict_hbm_if_needed(spill_to_cpu=True)'
)
# _access_swapmoe 中 self.hbm[uid] = g (swapmoe 不保留 CPU 镜像)
src = src.replace(
    '        self.hbm[uid] = g\n        self.hbm.move_to_end(uid)\n        self._evict_hbm_if_needed(spill_to_cpu=False)',
    '        self.hbm[uid] = (g, None)\n        self.hbm.move_to_end(uid)\n        self._evict_hbm_if_needed(spill_to_cpu=False)'
)
# _access_naive 和 _access_fiddler 中读取 self.hbm[uid] 改为 self.hbm[uid][0]
src = src.replace(
    '            return self.hbm[uid]\n',
    '            return self.hbm[uid][0]\n'
)
with open(path, 'w') as f: f.write(src)
PYEOF

# 1c. _evict_hbm_if_needed: 零拷贝淘汰
python3 << 'PYEOF'
import re
path = 'mecc_framework/cache/engine.py'
with open(path) as f: src = f.read()
old_evict = (
    '    def _evict_hbm_if_needed(self, spill_to_cpu: bool):\n'
    '        """HBM 满时淘汰最久未用的 expert。"""\n'
    '        while len(self.hbm) > self.k_h:\n'
    '            ev_uid, ev_ws = self.hbm.popitem(last=False)\n'
    '            if spill_to_cpu and self.k_c > 0:\n'
    '                self.cpu[ev_uid] = ev_ws.to("cpu")\n'
    '                self.cpu.move_to_end(ev_uid)\n'
    '                self._evict_cpu_if_needed()'
)
new_evict = (
    '    def _evict_hbm_if_needed(self, spill_to_cpu: bool):\n'
    '        """HBM 满时淘汰最久未用的 expert (零拷贝: 复用 CPU 镜像)。"""\n'
    '        while len(self.hbm) > self.k_h:\n'
    '            ev_uid, (ev_gpu, ev_cpu) = self.hbm.popitem(last=False)\n'
    '            if spill_to_cpu and self.k_c > 0 and ev_cpu is not None:\n'
    '                self.cpu[ev_uid] = ev_cpu\n'
    '                self.cpu.move_to_end(ev_uid)\n'
    '                self._evict_cpu_if_needed()'
)
src = src.replace(old_evict, new_evict)
with open(path, 'w') as f: f.write(src)
print('opt-1 applied: zero-copy HBM eviction')
PYEOF

run_e2e "01_zero_copy_evict"

# ────────────────────────────────────────────
# 汇总
# ────────────────────────────────────────────
cd $ROOT
python3 << PYEOF
import json, os
print()
print('=' * 70)
print('ABLATION SUMMARY')
print('=' * 70)
print(f"{'Step':<28} {'TTFT(ms)':>10} {'TPOT(ms)':>10} {'tok/s':>10} {'vs baseline':>14}")
baseline_tps = None
for f in sorted(os.listdir('$RESULT_DIR')):
    if not f.endswith('.json'): continue
    with open(os.path.join('$RESULT_DIR', f)) as fp:
        r = json.load(fp)['results']['ours']
    label = f.replace('.json','')
    ttft, tpot, tps = r['ttft_ms'], r['tpot_ms'], r['tokens_per_s']
    if baseline_tps is None:
        baseline_tps = tps
        delta = ''
    else:
        d = (tps - baseline_tps) / baseline_tps * 100
        delta = f'{d:+.1f}%'
    print(f"{label:<28} {ttft:>10.1f} {tpot:>10.1f} {tps:>10.2f} {delta:>14}")
print('=' * 70)
PYEOF

echo "Done. Results: $RESULT_DIR/"
