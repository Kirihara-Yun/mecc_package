#!/bin/bash
# MECC — 一键运行 (CPU 或 GPU)
# Usage: bash run_all.sh [gpu|cpu]

MODE=${1:-cpu}

echo "============================================"
echo "MECC — MoE Expert Cache Compiler"
echo "Mode: $MODE"
echo "============================================"

# 1. 编译器 (CPU only)
echo ""
echo "[1/4] Compiler Demo..."
python3 compiler.py

# 2. 缓存模拟器
echo ""
echo "[2/4] Cache Simulator..."
python3 scripts/tiered_cache.py

# 3. Runtime Spec
echo ""
echo "[3/4] Runtime Spec Demo..."
python3 runtime_spec.py

# 4. GPU Profiling (如果有GPU)
if [ "$MODE" = "gpu" ]; then
    echo ""
    echo "[4/4] GPU Profiling..."
    python3 scripts/profile_gpu.py
else
    echo ""
    echo "[4/4] GPU Profiling — SKIPPED (use 'bash run_all.sh gpu' on GPU server)"
fi

echo ""
echo "============================================"
echo "All done!"
echo "  Compiler: compiler.py → JSON config"
echo "  Runtime:  runtime_spec.py → get_expert() API"
echo "  GPU:      profile_gpu.py → calibrate parameters"
echo "============================================"
