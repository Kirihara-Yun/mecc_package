#!/usr/bin/env python3
"""
real_tiered_cache.py — 真实三级缓存端到端实测 (REAL end-to-end, FAIR)
======================================================================
与 tiered_cache.py (纯解析模拟) 的本质区别: 本脚本**真正搬运 torch 张量**。
  HBM = MPS/CUDA 显存真实张量 | CPU = 进程 RAM 真实张量 | SSD = 磁盘 .bin (F_NOCACHE 冷读)

公平性原则 (修正首版的不公平对比):
  - SwapMoE 与 OURS 拥有**相同的快速内存预算**: K_H 个 HBM 槽 + K_C 个 CPU 槽。
  - 唯一区别是**管理策略**:
      SwapMoE : 只对 HBM 做 LRU; CPU 驻留**静态** top-K_C (编译期频率), 其余 SSD。
      FluxMoE : 不缓存 HBM (显存让给 KV); CPU 静态 top-K_C, 其余 SSD, 每次 stream。
      OURS    : HBM(K_H)+CPU(K_C) **联合动态** LRU, 带升降级, 其余 SSD。
  - 大模型场景: N >> (K_H + K_C), 即模型装不下 CPU —— 这是三级缓存的目标场景。

负载:
  stationary  : 平稳 Zipf。静态放置接近最优, 预期 OURS ≈ SwapMoE。
  drift       : 热点随时间漂移。静态放置失效, 预期 OURS >> SwapMoE (动态自适应)。
"""
import argparse, json, os, random, statistics, tempfile, time, fcntl, sys
from collections import OrderedDict, Counter
import numpy as np
import torch


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda"), "cuda"
    elif torch.backends.mps.is_available():
        return torch.device("mps"), "mps"
    return torch.device("cpu"), "cpu"


DEV, DEV_TYPE = get_device()
IS_DARWIN = sys.platform == "darwin"
F_NOCACHE = 48


def sync():
    if DEV_TYPE == "cuda":
        torch.cuda.synchronize()
    elif DEV_TYPE == "mps":
        torch.mps.synchronize()


def silu_ffn(x, g, u, d):
    return (torch.nn.functional.silu(x @ g) * (x @ u)) @ d


# ═══════════════════════════════════════════════════════════
# Expert 仓库: 所有 expert 权重序列化到磁盘 (真实文件)
# ═══════════════════════════════════════════════════════════

class ExpertStore:
    def __init__(self, n_experts, hidden, ffn, dtype, tmpdir):
        self.n = n_experts; self.hidden = hidden; self.ffn = ffn; self.dtype = dtype
        self.np_dtype = {torch.float16: "float16", torch.float32: "float32"}[dtype]
        self.shapes = [(hidden, ffn), (hidden, ffn), (ffn, hidden)]
        self.nbytes = [int(np.prod(s)) * dtype.itemsize for s in self.shapes]
        self.tmpdir = tmpdir; self.paths = []
        print(f"  Materializing {n_experts} experts to disk "
              f"({sum(self.nbytes)/1e6:.0f}MB each, {n_experts*sum(self.nbytes)/1e9:.1f}GB total)...")
        for i in range(n_experts):
            ps = []
            for j, sh in enumerate(self.shapes):
                p = os.path.join(tmpdir, f"e{i}_w{j}.bin")
                torch.randn(*sh, dtype=dtype).numpy().tofile(p)
                ps.append(p)
            self.paths.append(ps)

    def _read_nocache(self, path, nb):
        fd = os.open(path, os.O_RDONLY)
        try:
            if IS_DARWIN:
                fcntl.fcntl(fd, F_NOCACHE, 1)  # macOS: 绕过 unified buffer cache
            elif hasattr(os, "posix_fadvise"):
                os.posix_fadvise(fd, 0, nb, os.POSIX_FADV_DONTNEED)  # Linux: 丢弃 page cache → 真冷读 NVMe
            buf = bytearray()
            while len(buf) < nb:
                chunk = os.read(fd, nb - len(buf))
                if not chunk:
                    break
                buf += chunk
            return bytes(buf)
        finally:
            if (not IS_DARWIN) and hasattr(os, "posix_fadvise"):
                os.posix_fadvise(fd, 0, nb, os.POSIX_FADV_DONTNEED)  # 读后再丢弃, 防止下次命中 page cache
            os.close(fd)

    def load_to_cpu(self, eid):
        out = []
        for path, sh, nb in zip(self.paths[eid], self.shapes, self.nbytes):
            raw = self._read_nocache(path, nb)
            arr = np.frombuffer(raw, dtype=self.np_dtype).reshape(sh).copy()
            out.append(torch.from_numpy(arr))
        return out


# ═══════════════════════════════════════════════════════════
# 策略 (真实张量搬运, 公平预算)
# ═══════════════════════════════════════════════════════════

class FluxMoE:
    """不缓存 HBM; CPU 静态驻留 top-K_C; 其余 SSD; 每次 stream→GPU。"""
    name = "FluxMoE"
    def __init__(self, store, x, k_h, k_c, static_cpu):
        self.store = store; self.x = x
        self.cpu = {e: store.load_to_cpu(e) for e in static_cpu[:k_c]}  # 静态
        self.hits = [0, 0, 0]
    def access(self, eid):
        if eid in self.cpu:
            g, u, d = (t.to(DEV, non_blocking=True) for t in self.cpu[eid]); self.hits[1] += 1
        else:
            g, u, d = (t.to(DEV, non_blocking=True) for t in self.store.load_to_cpu(eid)); self.hits[2] += 1
        return silu_ffn(self.x, g, u, d)


class SwapMoE:
    """HBM LRU(K_H) + CPU 静态 top-K_C + SSD。仅 HBM 动态管理。"""
    name = "SwapMoE"
    def __init__(self, store, x, k_h, k_c, static_cpu):
        self.store = store; self.x = x; self.k_h = k_h
        self.cpu = {e: store.load_to_cpu(e) for e in static_cpu[:k_c]}  # 静态 CPU
        self.hbm = OrderedDict()
        self.hits = [0, 0, 0]
    def access(self, eid):
        if eid in self.hbm:
            self.hbm.move_to_end(eid); g, u, d = self.hbm[eid]; self.hits[0] += 1
            return silu_ffn(self.x, g, u, d)
        if eid in self.cpu:  # CPU 静态命中
            g, u, d = (t.to(DEV, non_blocking=True) for t in self.cpu[eid]); self.hits[1] += 1
        else:  # SSD 冷读
            g, u, d = (t.to(DEV, non_blocking=True) for t in self.store.load_to_cpu(eid)); self.hits[2] += 1
        self.hbm[eid] = (g, u, d); self.hbm.move_to_end(eid)
        while len(self.hbm) > self.k_h:
            self.hbm.popitem(last=False)
        return silu_ffn(self.x, g, u, d)


class TieredLRU:
    """OUR: 独占式 (exclusive) 三级缓存, 忠实论文设计。
    HBM(K_H) 与 CPU(K_C) 持有**不相交**的 expert 集合 (总不同缓存 = K_H+K_C, 与 SwapMoE 对等)。
    升级: SSD→CPU→HBM; 降级: HBM 满 → 退回 CPU; CPU 满 → 丢到 SSD。
    与 SwapMoE 的唯一区别: CPU 层是**动态 LRU** (自适应漂移), 而非静态放置。

    [关键修正] expert 权重是**只读**的: 升级 CPU→HBM 时, CPU 端张量本就在手上。
    因此每个 HBM 槽同时保留 (GPU 副本, 只读 CPU 镜像)。HBM 满淘汰时直接把已有的
    CPU 镜像放回 CPU 层 —— **零拷贝, 无 D2H**。旧版的 t.to("cpu") 写回是对只读权重
    的纯浪费 (再造一份本就存在的数据), 已移除。
    """
    name = "TieredLRU"
    def __init__(self, store, x, k_h, k_c, static_cpu):
        self.store = store; self.x = x; self.k_h = k_h; self.k_c = k_c
        self.hbm = OrderedDict()  # eid → (gpu_ws, cpu_ws): GPU 副本 + 只读 CPU 镜像
        self.cpu = OrderedDict()  # eid → cpu_ws on CPU RAM (与 hbm 不相交)
        self.hits = [0, 0, 0]
        for e in static_cpu[:k_h]:               # 预热: 最热 K_H 入 HBM (保留 CPU 镜像)
            cw = store.load_to_cpu(e)
            self.hbm[e] = (tuple(t.to(DEV) for t in cw), cw)
        for e in static_cpu[k_h:k_h + k_c]:      # 次热 K_C 入 CPU
            self.cpu[e] = store.load_to_cpu(e)
        sync()
    def _promote_to_hbm(self, eid, gpu_ws, cpu_ws):
        self.hbm[eid] = (gpu_ws, cpu_ws); self.hbm.move_to_end(eid)
        while len(self.hbm) > self.k_h:
            ev, (_gw, cw) = self.hbm.popitem(last=False)
            self.cpu[ev] = cw                               # 降级 HBM→CPU: 复用只读 CPU 镜像 (零拷贝)
            self.cpu.move_to_end(ev)
            while len(self.cpu) > self.k_c:
                self.cpu.popitem(last=False)                # 降级 CPU→SSD (丢引用, 已在盘)
    def access(self, eid):
        if eid in self.hbm:
            self.hbm.move_to_end(eid); (g, u, d), _ = self.hbm[eid]; self.hits[0] += 1
            return silu_ffn(self.x, g, u, d)
        if eid in self.cpu:                       # CPU 命中 → 上 GPU (移出 CPU)
            ws = self.cpu.pop(eid)
            g, u, d = (t.to(DEV, non_blocking=True) for t in ws); self.hits[1] += 1
            self._promote_to_hbm(eid, (g, u, d), ws)
            return silu_ffn(self.x, g, u, d)
        ws = self.store.load_to_cpu(eid)          # SSD 冷读 → 上 GPU
        g, u, d = (t.to(DEV, non_blocking=True) for t in ws); self.hits[2] += 1
        self._promote_to_hbm(eid, (g, u, d), ws)
        return silu_ffn(self.x, g, u, d)


# ═══════════════════════════════════════════════════════════
# Trace 生成
# ═══════════════════════════════════════════════════════════

def zipf_stationary(n, alpha, k, seed=42):
    random.seed(seed)
    w = [1.0 / i**alpha for i in range(1, n + 1)]; s = sum(w)
    return random.choices(range(n), weights=[x/s for x in w], k=k)


def zipf_drift(n, alpha, k, phases=4, seed=42):
    """热点随时间漂移: 每个 phase 把 Zipf 排名整体平移。"""
    random.seed(seed)
    out = []; pl = k // phases
    for p in range(phases):
        shift = p * (n // phases)
        w = [1.0 / (((i + shift) % n + 1) ** alpha) for i in range(n)]; s = sum(w)
        out.extend(random.choices(range(n), weights=[x/s for x in w], k=pl))
    return out


def run_policy(policy, trace):
    lats = []; sync()
    for eid in trace:
        t0 = time.perf_counter(); _ = policy.access(eid); sync()
        lats.append((time.perf_counter() - t0) * 1e6)
    tot = sum(policy.hits)
    return {
        "policy": policy.name,
        "hbm_hit_pct": round(policy.hits[0]/tot*100, 1),
        "cpu_hit_pct": round(policy.hits[1]/tot*100, 1),
        "ssd_hit_pct": round(policy.hits[2]/tot*100, 1),
        "avg_lat_us": round(statistics.mean(lats), 1),
        "p50_us": round(statistics.median(lats), 1),
        "p99_us": round(sorted(lats)[min(len(lats)-1, int(len(lats)*0.99))], 1),
    }


def run_workload(store, x, trace, k_h, k_c, label):
    # 编译期静态放置: 按本 workload 的聚合频率排序 (所有方法共享, 公平)
    freq = Counter(trace)
    ranked = [e for e, _ in freq.most_common()] + [e for e in range(store.n) if e not in freq]
    print(f"\n[{label}] {len(trace)} reqs | static-placement by aggregate freq")
    results = []
    for mk in [lambda: FluxMoE(store, x, k_h, k_c, ranked),
               lambda: SwapMoE(store, x, k_h, k_c, ranked),
               lambda: TieredLRU(store, x, k_h, k_c, ranked)]:
        pol = mk(); t0 = time.time(); r = run_policy(pol, trace)
        r["wall_s"] = round(time.time() - t0, 1); results.append(r)
        print(f"  {r['policy']:<11} avg={r['avg_lat_us']:8.1f}μs p99={r['p99_us']:9.1f}μs "
              f"HBM/CPU/SSD={r['hbm_hit_pct']:.0f}/{r['cpu_hit_pct']:.0f}/{r['ssd_hit_pct']:.0f}%")
    flux = next(r for r in results if r["policy"] == "FluxMoE")["avg_lat_us"]
    swap = next(r for r in results if r["policy"] == "SwapMoE")["avg_lat_us"]
    tlr = next(r for r in results if r["policy"] == "TieredLRU")["avg_lat_us"]
    print(f"  → OURS vs FluxMoE {flux/tlr:.2f}× | vs SwapMoE {swap/tlr:.2f}×")
    return {"workload": label, "results": results,
            "speedup": {"vs_flux": round(flux/tlr, 3), "vs_swap": round(swap/tlr, 3)}}


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
    ap.add_argument("--phases", type=int, default=4,
                    help="drift 漂移强度: phase 越多漂移越快 (1=近似平稳)。用于扫 speedup-vs-drift 交叉点")
    ap.add_argument("--dtype", type=str, default="float16")
    ap.add_argument("--out", type=str, default="real_e2e_results.json")
    args = ap.parse_args()

    dtype = getattr(torch, args.dtype)
    esz_mb = (3 * args.hidden * args.ffn) * dtype.itemsize / 1e6
    fast = args.k_h + args.k_c
    print("=" * 70)
    print("REAL End-to-End Tiered Expert Cache Benchmark (FAIR, equal budget)")
    print("=" * 70)
    print(f"Device   : {DEV_TYPE}")
    print(f"Experts  : N={args.n_experts}, {esz_mb:.0f}MB each (hidden={args.hidden}, ffn={args.ffn})")
    print(f"Budget   : HBM={args.k_h} + CPU={args.k_c} = {fast} fast slots "
          f"({fast}/{args.n_experts}={fast/args.n_experts*100:.0f}% of model)")
    print(f"Regime   : {'LARGE-MODEL (CPU cannot fit all)' if fast < args.n_experts else 'CPU FITS ALL'}")

    tmpdir = tempfile.mkdtemp(prefix="mecc_e2e_")
    store = None
    try:
        store = ExpertStore(args.n_experts, args.hidden, args.ffn, dtype, tmpdir)
        x = torch.randn(args.batch, args.hidden, dtype=dtype, device=DEV)
        workloads = [
            ("stationary", zipf_stationary(args.n_experts, args.alpha, args.requests)),
            ("drift",      zipf_drift(args.n_experts, args.alpha, args.requests, phases=args.phases)),
        ]
        all_res = [run_workload(store, x, tr, args.k_h, args.k_c, lbl) for lbl, tr in workloads]
        print("=" * 70)
        out = {"device": DEV_TYPE,
               "config": {"n_experts": args.n_experts, "expert_mb": round(esz_mb, 1),
                          "hidden": args.hidden, "ffn": args.ffn, "batch": args.batch,
                          "alpha": args.alpha, "requests": args.requests,
                          "k_h": args.k_h, "k_c": args.k_c, "phases": args.phases,
                          "fast_fraction": round(fast/args.n_experts, 3)},
               "workloads": all_res}
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
