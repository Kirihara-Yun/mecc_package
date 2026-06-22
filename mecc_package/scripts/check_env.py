#!/usr/bin/env python3
"""
MECC 环境与适用性自检
=====================
零第三方依赖（仅标准库），任何机器都能跑：

  python3 scripts/check_env.py                          # 检查环境 + import 链
  python3 scripts/check_env.py --applies \\
      --n-layers 32 --n-experts 8 --expert-gb 0.336 \\
      --cpu-gb 64 --hbm-gb 32                            # 判断某模型在某机器上 MECC 是否适用

适用性判据（见 docs/APPLICABILITY.md）：
  MECC 仅在「模型 expert 总量 > 可用 CPU 内存」（被迫落 SSD）时才有价值。
"""
import argparse
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # mecc_package/


def _ok(msg):   print(f"  [ OK ] {msg}")
def _warn(msg): print(f"  [WARN] {msg}")
def _fail(msg): print(f"  [FAIL] {msg}")


def check_python():
    print("== Python ==")
    v = sys.version_info
    if v >= (3, 8):
        _ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        _warn(f"Python {v.major}.{v.minor}（建议 >= 3.8）")


def check_optional_deps():
    print("== 可选运行时依赖（端到端实验才需要）==")
    for mod, note in [
        ("numpy", "编译器/模拟器必需"),
        ("torch", "GPU 端到端必需（5090 需 cu124+ nightly）"),
        ("transformers", "加载 HF 模型必需"),
        ("safetensors", "流式抽取 expert 权重必需"),
    ]:
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "?")
            _ok(f"{mod} {ver}（{note}）")
        except Exception:
            _warn(f"{mod} 缺失（{note}）—— 纯文档/适用性判断无需它")


def check_import_chain():
    """验证 AGENTS.md 第 3 节的硬约束 import 链未被破坏。"""
    print("== import 链完整性（硬约束）==")
    checks = [
        (os.path.join(ROOT, "e2e"), "compile_config", "e2e → 根级 compiler.py（sys.path 跨目录）"),
        (ROOT, "runtime_spec", "runtime_spec → compiler"),
        (os.path.join(ROOT, "scripts"), "concurrent_tiered_cache", "scripts 内部 concurrent → real_tiered_cache"),
    ]
    all_pass = True
    for path, mod, desc in checks:
        saved = sys.path[:]
        sys.path.insert(0, path)
        for m in list(sys.modules):
            if m in (mod, "compiler", "real_tiered_cache"):
                sys.modules.pop(m, None)
        try:
            importlib.import_module(mod)
            _ok(f"{desc}")
        except ModuleNotFoundError as e:
            # torch 等运行时依赖缺失不算断链，只要本地模块已解析
            if e.name in ("torch", "transformers", "safetensors", "numpy", "datasets"):
                _ok(f"{desc}（本地模块已解析；运行时依赖 {e.name} 缺失，与组织无关）")
            else:
                _fail(f"{desc} —— 本地模块 {e.name} 找不到，可能违反硬约束！")
                all_pass = False
        except Exception as e:
            _warn(f"{desc} —— {type(e).__name__}: {e}")
        finally:
            sys.path[:] = saved
    return all_pass


def check_applicability(args):
    """按 docs/APPLICABILITY.md 决策树判断 MECC 是否适用。"""
    print("== 适用性判断（docs/APPLICABILITY.md）==")
    expert_total = args.n_layers * args.n_experts * args.expert_gb
    print(f"  模型 expert 总量 ≈ {args.n_layers} 层 × {args.n_experts} experts × "
          f"{args.expert_gb}GB = {expert_total:.1f} GB (fp16)")
    print(f"  可用 HBM = {args.hbm_gb} GB | 可用 CPU 内存 = {args.cpu_gb} GB")
    print("  " + "-" * 50)

    if expert_total <= args.hbm_gb:
        print("  >>> 结论：模型能塞进 HBM → 不需要 offload，MECC 无意义。 ❌")
    elif expert_total <= args.cpu_gb:
        print("  >>> 结论：HBM 装不下但 CPU 装得下 → 两级方案足够，"
              "MECC 无结构性优势（第三级 SSD 用不上）。 ⚠️")
    else:
        deficit = expert_total - args.cpu_gb
        print(f"  >>> 结论：连 CPU 也装不下（缺 {deficit:.1f} GB，需落 SSD）→ "
              "★ MECC 有效区 ★ ✅")
        print("      三级缓存 + 编译器放置将带来收益。建议开 --cold_ssd 跑真实端到端。")


def main():
    ap = argparse.ArgumentParser(description="MECC 环境与适用性自检")
    ap.add_argument("--applies", action="store_true", help="执行适用性判断")
    ap.add_argument("--n-layers", type=int, default=32)
    ap.add_argument("--n-experts", type=int, default=8, help="每层 routed expert 数")
    ap.add_argument("--expert-gb", type=float, default=0.336, help="单 expert 大小(GB, fp16)")
    ap.add_argument("--cpu-gb", type=float, default=64, help="可用 CPU 内存(GB)")
    ap.add_argument("--hbm-gb", type=float, default=32, help="可用 GPU 显存(GB)")
    args = ap.parse_args()

    print("MECC self-check\n" + "=" * 40)
    check_python()
    check_optional_deps()
    chain_ok = check_import_chain()
    if args.applies:
        check_applicability(args)

    print("=" * 40)
    print("完成。" + ("" if chain_ok else " ⚠️ 存在 import 链问题，请对照 AGENTS.md 第 3 节。"))
    sys.exit(0 if chain_ok else 1)


if __name__ == "__main__":
    main()
