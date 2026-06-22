#!/usr/bin/env python3
"""
concurrent_tiered_cache.py — 并发/吞吐压测 (CONCURRENT, saturation regime)
==========================================================================
回答的核心问题: "CPU/带宽被占满时, 分层缓存到底赢多少?"

与 real_tiered_cache.py 的本质区别:
  real_tiered_cache.py : 纯串行, 每次 access 后立即 sync。任意时刻只有 1 个
                         expert 在搬运或 1 次 GEMM 在算 → 硬件全程空闲, 永远
                         进不了"占满"工况。它测的是**轻载单请求 avg latency**。
  本脚本               : 闭环并发 (C 个请求 in-flight), 搬运与计算**流水线重叠**,
                         真实硬件资源 (磁盘 IO / 拷贝引擎 / GPU 计算) 被多个请求
                         同时争用 → 带宽真正饱和。测的是**吞吐 + 排队后的 p99**。

公平性 (steelman 对手):
  - 所有策略都享受 copy/compute overlap: 第 N+1 个请求的 H2D 搬运与第 N 个请求
    的 GEMM 计算并行。对手 FluxMoE/SwapMoE 的"每次 stream"因此可以被前一个
    请求的计算掩盖掉 —— 这正是 overlap 能否抵消高搬运量的关键检验。
  - CUDA: 独立 copy_stream + compute_stream + event, 真实拷贝引擎/计算引擎重叠
          (= A100 真实行为)。
  - MPS/CPU: 无多 stream, device 操作串行化 (device_lock), 但磁盘 IO 仍并行,
            UMA 下 H2D 近乎零拷贝, 故 Apple 的瓶颈本就主要在磁盘 IO。
            overlap 受限会**低估** OURS 在 A100 上的收益, 此处如实标注。

输出指标:
  throughput (req/s)  : 占满工况下最该看的指标
  p50 / p99 (μs)      : 端到端延迟, **含排队等待** (不是独占延迟)
  hit rates           : 与串行版一致 (命中率硬件/并发无关)

典型预期 (待实测证实):
  C=1  : 退化为串行, OURS ≈ 串行版结论 (stationary 可能不占优)。
  C↑   : 搬运排队 → 高 HBM 命中的 OURS 吞吐/​p99 优势随并发上升而放大 (若成立)。
         若对手 overlap 足以掩盖搬运, 则 OURS 优势被抹平 (这同样是有价值的结论)。
"""
import argparse, json, os, statistics, tempfile, threading, time
from collections import OrderedDict, Counter
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import torch

from real_tiered_cache import (
    ExpertStore, silu_ffn, zipf_stationary, zipf_drift,
    DEV, DEV_TYPE, sync,
)

IS_CUDA = (DEV_TYPE == "cuda")

# ─────────────────────────────────────────────────────────────
# 设备执行引擎: 在 CUDA 上用双 stream 做真实 copy/compute overlap;
#              在 MPS/CPU 上退化为 device_lock 串行 (磁盘 IO 仍并行)。
# ─────────────────────────────────────────────────────────────
_device_lock = threading.Lock()
if IS_CUDA:
    _copy_stream = torch.cuda.Stream()
    _compute_stream = torch.cuda.Stream()


def h2d_and_compute(x, cpu_ws):
    """把 CPU 张量搬到 device 并跑一次 FFN。返回 (out, gpu_ws)。
    CUDA: H2D 在 copy_stream, GEMM 在 compute_stream, 经 event 串接 → 与其他请求重叠。
    其他: device_lock 内串行 (仍允许磁盘 IO 与之并行)。
    """
    if IS_CUDA:
        with _device_lock:
            with torch.cuda.stream(_copy_stream):
                gpu_ws = tuple(t.to(DEV, non_blocking=True) for t in cpu_ws)
            ev = torch.cuda.Event()
            ev.record(_copy_stream)
            with torch.cuda.stream(_compute_stream):
                _compute_stream.wait_event(ev)
                out = silu_ffn(x, *gpu_ws)
            done = torch.cuda.Event()
            done.record(_compute_stream)
        done.synchronize()          # 锁外等待 → 流水线可被其他线程填充
        return out, gpu_ws
    else:
        with _device_lock:
            gpu_ws = tuple(t.to(DEV, non_blocking=True) for t in cpu_ws)
            out = silu_ffn(x, *gpu_ws)
            sync()
        return out, gpu_ws


def compute_only(x, gpu_ws):
    """HBM 命中: 权重已在 device, 仅 GEMM。"""
    if IS_CUDA:
        with _device_lock:
            with torch.cuda.stream(_compute_stream):
                out = silu_ffn(x, *gpu_ws)
            done = torch.cuda.Event()
            done.record(_compute_stream)
        done.synchronize()
        return out
    else:
        with _device_lock:
            out = silu_ffn(x, *gpu_ws)
            sync()
        return out


# ─────────────────────────────────────────────────────────────
# 路由计划: route() 只做"决策 + 缓存簿记", 不碰真正的 device 搬运。
#   Plan(tier, gpu_ws, cpu_ws, need_disk, commit)
#     tier0 HBM命中 : gpu_ws 已就绪, commit=None
#     tier1 CPU命中 : cpu_ws 为 RAM 张量, 需 H2D, commit 写回 HBM
#     tier2 SSD冷读 : need_disk=True, worker 读盘得 cpu_ws, commit 写回 HBM
# ─────────────────────────────────────────────────────────────
class Plan:
    __slots__ = ("tier", "gpu_ws", "cpu_ws", "need_disk", "commit")
    def __init__(self, tier, gpu_ws=None, cpu_ws=None, need_disk=False, commit=None):
        self.tier = tier; self.gpu_ws = gpu_ws; self.cpu_ws = cpu_ws
        self.need_disk = need_disk; self.commit = commit


class PFlux:
    """不缓存 HBM; CPU 静态 top-K_C; 其余 SSD。每次都要 H2D (tier1) 或 读盘+H2D (tier2)。"""
    name = "FluxMoE"
    def __init__(self, store, k_h, k_c, ranked):
        self.store = store
        self.cpu = {e: store.load_to_cpu(e) for e in ranked[:k_c]}
        self.hits = [0, 0, 0]
        self.lock = threading.Lock()
    def route(self, eid):
        with self.lock:
            if eid in self.cpu:
                self.hits[1] += 1
                return Plan(1, cpu_ws=self.cpu[eid])
            self.hits[2] += 1
            return Plan(2, need_disk=True)


class PSwap:
    """HBM LRU(K_H) + CPU 静态 top-K_C + SSD。仅 HBM 动态。降级仅丢引用 (CPU 静态, 无 D2H)。"""
    name = "SwapMoE"
    def __init__(self, store, k_h, k_c, ranked):
        self.store = store; self.k_h = k_h
        self.cpu = {e: store.load_to_cpu(e) for e in ranked[:k_c]}
        self.hbm = OrderedDict()
        self.hits = [0, 0, 0]
        self.lock = threading.Lock()
    def route(self, eid):
        with self.lock:
            if eid in self.hbm:
                self.hbm.move_to_end(eid)
                self.hits[0] += 1
                return Plan(0, gpu_ws=self.hbm[eid])
            if eid in self.cpu:
                self.hits[1] += 1; cpu_ws = self.cpu[eid]; tier = 1; need = False
            else:
                self.hits[2] += 1; cpu_ws = None; tier = 2; need = True
            def commit(gpu_ws, cpu_ws=None, _eid=eid):
                with self.lock:
                    self.hbm[_eid] = gpu_ws; self.hbm.move_to_end(_eid)
                    while len(self.hbm) > self.k_h:
                        self.hbm.popitem(last=False)   # 丢引用即可
            return Plan(tier, cpu_ws=cpu_ws, need_disk=need, commit=commit)


class PTiered:
    """OURS: 独占式 HBM(K_H)+CPU(K_C) 动态 LRU。升级 SSD→CPU→HBM; HBM 满 → 退回 CPU。
    [关键修正] expert 权重只读: 每个 HBM 槽保留 (gpu_ws, 只读 CPU 镜像), 淘汰时直接把
    镜像放回 CPU 层 —— 零拷贝, 无 D2H (旧版 t.to('cpu') 写回是对只读权重的纯浪费)。"""
    name = "TieredLRU"
    def __init__(self, store, k_h, k_c, ranked):
        self.store = store; self.k_h = k_h; self.k_c = k_c
        self.hbm = OrderedDict(); self.cpu = OrderedDict()
        self.hits = [0, 0, 0]
        self.lock = threading.Lock()
        for e in ranked[:k_h]:
            cw = store.load_to_cpu(e)
            self.hbm[e] = (tuple(t.to(DEV) for t in cw), cw)   # GPU 副本 + 只读 CPU 镜像
        for e in ranked[k_h:k_h + k_c]:
            self.cpu[e] = store.load_to_cpu(e)
        sync()
    def route(self, eid):
        with self.lock:
            if eid in self.hbm:
                self.hbm.move_to_end(eid)
                self.hits[0] += 1
                return Plan(0, gpu_ws=self.hbm[eid][0])
            if eid in self.cpu:
                cpu_ws = self.cpu.pop(eid); self.hits[1] += 1; tier = 1; need = False
            else:
                cpu_ws = None; self.hits[2] += 1; tier = 2; need = True
            def commit(gpu_ws, cpu_ws_real, _eid=eid):
                with self.lock:
                    self.hbm[_eid] = (gpu_ws, cpu_ws_real); self.hbm.move_to_end(_eid)
                    while len(self.hbm) > self.k_h:
                        ev, (_gw, cw) = self.hbm.popitem(last=False)
                        self.cpu[ev] = cw; self.cpu.move_to_end(ev)   # 复用只读 CPU 镜像, 零拷贝
                        while len(self.cpu) > self.k_c:
                            self.cpu.popitem(last=False)
            return Plan(tier, cpu_ws=cpu_ws, need_disk=need, commit=commit)


# ─────────────────────────────────────────────────────────────
# 闭环并发执行器
# ─────────────────────────────────────────────────────────────
def run_concurrent(policy, store, x, trace, concurrency):
    """C 个 worker 线程, 每个不断领取下一个请求并端到端执行 (含真实搬运/读盘)。
    返回吞吐与含排队的延迟分布。"""
    idx = {"i": 0}
    idx_lock = threading.Lock()
    lats = [0.0] * len(trace)
    sync()
    t_start = time.perf_counter()

    def worker():
        while True:
            with idx_lock:
                i = idx["i"]
                if i >= len(trace):
                    return
                idx["i"] = i + 1
            eid = trace[i]
            t0 = time.perf_counter()
            plan = policy.route(eid)
            if plan.tier == 0:
                compute_only(x, plan.gpu_ws)
            else:
                cpu_ws = store.load_to_cpu(eid) if plan.need_disk else plan.cpu_ws
                _, gpu_ws = h2d_and_compute(x, cpu_ws)
                if plan.commit is not None:
                    plan.commit(gpu_ws, cpu_ws)
            lats[i] = (time.perf_counter() - t0) * 1e6

    threads = [threading.Thread(target=worker) for _ in range(concurrency)]
    for t in threads: t.start()
    for t in threads: t.join()
    wall = time.perf_counter() - t_start

    tot = sum(policy.hits)
    sl = sorted(lats)
    return {
        "policy": policy.name,
        "concurrency": concurrency,
        "throughput_rps": round(len(trace) / wall, 1),
        "wall_s": round(wall, 2),
        "avg_lat_us": round(statistics.mean(lats), 1),
        "p50_us": round(statistics.median(lats), 1),
        "p99_us": round(sl[min(len(sl) - 1, int(len(sl) * 0.99))], 1),
        "hbm_hit_pct": round(policy.hits[0] / tot * 100, 1),
        "cpu_hit_pct": round(policy.hits[1] / tot * 100, 1),
        "ssd_hit_pct": round(policy.hits[2] / tot * 100, 1),
    }


def run_workload(store, x, trace, k_h, k_c, label, concurrencies):
    freq = Counter(trace)
    ranked = [e for e, _ in freq.most_common()] + [e for e in range(store.n) if e not in freq]
    print(f"\n[{label}] {len(trace)} reqs | concurrency sweep {concurrencies}")
    rows = []
    for C in concurrencies:
        builders = [
            ("FluxMoE",   lambda: PFlux(store, k_h, k_c, ranked)),
            ("SwapMoE",   lambda: PSwap(store, k_h, k_c, ranked)),
            ("TieredLRU", lambda: PTiered(store, k_h, k_c, ranked)),
        ]
        res = {}
        for _, mk in builders:
            pol = mk()
            r = run_concurrent(pol, store, x, trace, C)
            res[r["policy"]] = r
            rows.append({"workload": label, **r})
        flux = res["FluxMoE"]; swap = res["SwapMoE"]; ours = res["TieredLRU"]
        # 吞吐越高越好 → OURS/对手; 延迟越低越好 → 对手/OURS
        tp_vs_flux = ours["throughput_rps"] / flux["throughput_rps"]
        tp_vs_swap = ours["throughput_rps"] / swap["throughput_rps"]
        p99_vs_flux = flux["p99_us"] / ours["p99_us"]
        p99_vs_swap = swap["p99_us"] / ours["p99_us"]
        print(f"  C={C:<3} | "
              f"Flux tp={flux['throughput_rps']:7.1f} p99={flux['p99_us']:8.1f} | "
              f"Swap tp={swap['throughput_rps']:7.1f} p99={swap['p99_us']:8.1f} | "
              f"OURS tp={ours['throughput_rps']:7.1f} p99={ours['p99_us']:8.1f} "
              f"HBM={ours['hbm_hit_pct']:.0f}%")
        print(f"        → OURS throughput vs Flux {tp_vs_flux:.2f}× vs Swap {tp_vs_swap:.2f}× | "
              f"p99 vs Flux {p99_vs_flux:.2f}× vs Swap {p99_vs_swap:.2f}×")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_experts", type=int, default=96)
    ap.add_argument("--hidden", type=int, default=2048)
    ap.add_argument("--ffn", type=int, default=8192)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--alpha", type=float, default=1.2)
    ap.add_argument("--requests", type=int, default=600)
    ap.add_argument("--k_h", type=int, default=8)
    ap.add_argument("--k_c", type=int, default=16)
    ap.add_argument("--dtype", type=str, default="float16")
    ap.add_argument("--concurrency", type=str, default="1,4,16,32",
                    help="逗号分隔的并发档位")
    ap.add_argument("--out", type=str, default="concurrent_results.json")
    args = ap.parse_args()

    concurrencies = [int(c) for c in args.concurrency.split(",") if c.strip()]
    dtype = getattr(torch, args.dtype)
    esz_mb = (3 * args.hidden * args.ffn) * dtype.itemsize / 1e6
    fast = args.k_h + args.k_c
    print("=" * 72)
    print("CONCURRENT Tiered Expert Cache Benchmark (saturation regime, FAIR)")
    print("=" * 72)
    print(f"Device   : {DEV_TYPE}  ({'CUDA dual-stream overlap' if IS_CUDA else 'MPS/CPU: device serialized, IO parallel (overlap UNDERSTATED)'})")
    print(f"Experts  : N={args.n_experts}, {esz_mb:.0f}MB each (hidden={args.hidden}, ffn={args.ffn})")
    print(f"Budget   : HBM={args.k_h} + CPU={args.k_c} = {fast}/{args.n_experts} "
          f"({fast/args.n_experts*100:.0f}% of model)")
    print(f"Concurr. : {concurrencies}")

    tmpdir = tempfile.mkdtemp(prefix="mecc_conc_")
    store = None
    try:
        store = ExpertStore(args.n_experts, args.hidden, args.ffn, dtype, tmpdir)
        x = torch.randn(args.batch, args.hidden, dtype=dtype, device=DEV)
        workloads = [
            ("stationary", zipf_stationary(args.n_experts, args.alpha, args.requests)),
            ("drift",      zipf_drift(args.n_experts, args.alpha, args.requests)),
        ]
        all_rows = []
        for lbl, tr in workloads:
            all_rows += run_workload(store, x, tr, args.k_h, args.k_c, lbl, concurrencies)
        print("=" * 72)
        out = {"device": DEV_TYPE, "overlap": "cuda_dual_stream" if IS_CUDA else "serialized_io_parallel",
               "config": {"n_experts": args.n_experts, "expert_mb": round(esz_mb, 1),
                          "hidden": args.hidden, "ffn": args.ffn, "batch": args.batch,
                          "alpha": args.alpha, "requests": args.requests,
                          "k_h": args.k_h, "k_c": args.k_c,
                          "concurrency": concurrencies},
               "rows": all_rows}
        with open(args.out, "w") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"Saved → {args.out}")
    finally:
        if store:
            for ps in store.paths:
                for p in ps:
                    try: os.unlink(p)
                    except OSError: pass
        try: os.rmdir(tmpdir)
        except OSError: pass


if __name__ == "__main__":
    main()
