#!/usr/bin/env python3
"""
measure_tiers.py — 真实三级存储延迟测量 (REAL hardware measurement)
====================================================================
目的: 替换 proofs.md / tiered_cache.py 中**手写/伪造**的延迟常数
     (176 / 3510 / 50100 μs), 用本机真实测量值。

关键修正 (vs 旧 profile_gpu.py):
  旧版用 tensor.sum() / .mean() 测量, 这是 GPU **计算**延迟, 与缓存无关。
  三级缓存真正的延迟差异来自 **数据搬运**:
    - HBM hit : expert 权重已在 GPU 显存 → 仅 GEMM 计算 (无搬运)
    - CPU hit : expert 在 CPU RAM → 需 host→device 搬运 → 再计算
    - SSD miss: expert 在磁盘 → 读盘→CPU→device 搬运 → 再计算

  本脚本测量真实的 **端到端 expert 取用 + 一次前向 GEMM** 时间。

注意: Apple Silicon 是统一内存架构 (UMA), host↔device 可能近乎零拷贝,
     这本身就是一个值得记录的真实发现 (改变了 tier 经济学)。
"""
import argparse, json, os, statistics, tempfile, time
import torch


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda"), "cuda"
    elif torch.backends.mps.is_available():
        return torch.device("mps"), "mps"
    return torch.device("cpu"), "cpu"


def sync(dev_type):
    if dev_type == "cuda":
        torch.cuda.synchronize()
    elif dev_type == "mps":
        torch.mps.synchronize()


def make_expert_tensors(hidden, ffn, dtype, pin=False):
    """构造一个真实 expert 的三个权重矩阵 (gate, up, down) — 在 CPU 上。
    Mixtral expert: gate[h,f] up[h,f] down[f,h], SwiGLU FFN。
    """
    g = torch.randn(hidden, ffn, dtype=dtype)
    u = torch.randn(hidden, ffn, dtype=dtype)
    d = torch.randn(ffn, hidden, dtype=dtype)
    if pin and torch.cuda.is_available():
        g, u, d = g.pin_memory(), u.pin_memory(), d.pin_memory()
    return g, u, d


def expert_forward(x, g, u, d):
    """SwiGLU FFN 前向: down(silu(x@gate) * (x@up))。"""
    h = torch.nn.functional.silu(x @ g) * (x @ u)
    return h @ d


def measure(fn, dev_type, warmup=3, trials=12):
    """测量 fn 的执行时间 (μs), 返回 median。"""
    for _ in range(warmup):
        fn()
    sync(dev_type)
    ts = []
    for _ in range(trials):
        t0 = time.perf_counter()
        fn()
        sync(dev_type)
        ts.append((time.perf_counter() - t0) * 1e6)
    return statistics.median(ts), (statistics.pstdev(ts) if len(ts) > 1 else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hidden", type=int, default=4096, help="hidden dim (Mixtral=4096)")
    ap.add_argument("--ffn", type=int, default=14336, help="ffn dim (Mixtral=14336)")
    ap.add_argument("--batch", type=int, default=64, help="tokens routed to this expert")
    ap.add_argument("--dtype", type=str, default="float16")
    ap.add_argument("--out", type=str, default="measured_latency.json")
    args = ap.parse_args()

    dtype = getattr(torch, args.dtype)
    dev, dev_type = get_device()
    print("=" * 68)
    print("REAL Tier Latency Measurement")
    print("=" * 68)
    print(f"Device       : {dev_type}")
    print(f"Expert shape : gate/up[{args.hidden},{args.ffn}] down[{args.ffn},{args.hidden}] {args.dtype}")
    esz_bytes = (2 * args.hidden * args.ffn + args.ffn * args.hidden) * dtype.itemsize
    esz_mb = esz_bytes / (1024 * 1024)
    print(f"Expert size  : {esz_mb:.1f} MB ({args.dtype})")
    print(f"Token batch  : {args.batch}")
    print("-" * 68)

    # 输入激活 (always on device — 它是 hidden_states, 一直在 GPU)
    x = torch.randn(args.batch, args.hidden, dtype=dtype, device=dev)

    # ---------------------------------------------------------------
    # TIER 1: HBM hit — 权重常驻 GPU 显存, 只算 GEMM
    # ---------------------------------------------------------------
    g_d = torch.randn(args.hidden, args.ffn, dtype=dtype, device=dev)
    u_d = torch.randn(args.hidden, args.ffn, dtype=dtype, device=dev)
    d_d = torch.randn(args.ffn, args.hidden, dtype=dtype, device=dev)

    def hbm_hit():
        return expert_forward(x, g_d, u_d, d_d)

    t_hbm, s_hbm = measure(hbm_hit, dev_type)
    print(f"[HBM hit ]  compute only        : {t_hbm:8.1f} μs  (±{s_hbm:.1f})")

    # ---------------------------------------------------------------
    # TIER 2: CPU hit — 权重在 CPU RAM, 需 host→device 搬运 + GEMM
    # [修正] 必须用 pinned (page-locked) memory: 否则 non_blocking 失效, 且 PCIe
    #        走 pageable 暂存拷贝, 有效带宽掉到 ~6-7 GB/s (虚高 T_CPU 5-7x)。
    #        SwapMoE/FluxMoE 等真实 offload 系统均用 pinned, 这才是公平口径。
    # ---------------------------------------------------------------
    g_c, u_c, d_c = make_expert_tensors(args.hidden, args.ffn, dtype, pin=True)

    def cpu_hit():
        gg = g_c.to(dev, non_blocking=True)
        uu = u_c.to(dev, non_blocking=True)
        dd = d_c.to(dev, non_blocking=True)
        return expert_forward(x, gg, uu, dd)

    t_cpu, s_cpu = measure(cpu_hit, dev_type)
    print(f"[CPU hit ]  H2D transfer + compute: {t_cpu:8.1f} μs  (±{s_cpu:.1f})  [pinned/page-locked]")

    # 纯搬运成本 (不含计算)
    def cpu_transfer_only():
        return (g_c.to(dev, non_blocking=True),
                u_c.to(dev, non_blocking=True),
                d_c.to(dev, non_blocking=True))

    t_cpu_xfer, _ = measure(cpu_transfer_only, dev_type)
    print(f"            └─ transfer only     : {t_cpu_xfer:8.1f} μs"
          f"  (eff BW {esz_mb/1024/(t_cpu_xfer/1e6):.1f} GB/s)")

    # ---------------------------------------------------------------
    # TIER 3: SSD miss — 权重在磁盘, 需 read→CPU→device 搬运 + GEMM
    # ---------------------------------------------------------------
    import numpy as np
    import fcntl, sys as _sys
    tmpdir = tempfile.mkdtemp(prefix="mecc_ssd_")
    shapes = [(args.hidden, args.ffn), (args.hidden, args.ffn), (args.ffn, args.hidden)]
    np_dtype = {torch.float16: "float16", torch.float32: "float32",
                torch.bfloat16: "float16"}[dtype]
    nbytes = [int(np.prod(sh)) * dtype.itemsize for sh in shapes]

    # 为了真实冷读: 预生成多份副本, 每次 trial 读不同副本, 配合 F_NOCACHE 绕过 page cache
    n_copies = 8
    copy_paths = []
    for c in range(n_copies):
        ps = []
        for i, t in enumerate((g_c, u_c, d_c)):
            p = os.path.join(tmpdir, f"c{c}_w{i}.bin")
            t.numpy().tofile(p)
            ps.append(p)
        copy_paths.append(ps)

    IS_DARWIN = _sys.platform == "darwin"
    F_NOCACHE = 48  # macOS fcntl: disable data caching for this fd

    def _read_nocache(path, nbyte):
        fd = os.open(path, os.O_RDONLY)
        try:
            if IS_DARWIN:
                fcntl.fcntl(fd, F_NOCACHE, 1)  # macOS: 绕过 unified buffer cache → 真实 NVMe 读
            elif hasattr(os, "posix_fadvise"):
                os.posix_fadvise(fd, 0, nbyte, os.POSIX_FADV_DONTNEED)  # Linux: 丢弃本文件 page cache → 真冷读
            buf = b""
            while len(buf) < nbyte:
                chunk = os.read(fd, nbyte - len(buf))
                if not chunk:
                    break
                buf += chunk
            return buf
        finally:
            if (not IS_DARWIN) and hasattr(os, "posix_fadvise"):
                os.posix_fadvise(fd, 0, nbyte, os.POSIX_FADV_DONTNEED)  # 读后再丢弃, 保证下次仍冷
            os.close(fd)

    _trial = {"i": 0}

    def ssd_miss():
        ps = copy_paths[_trial["i"] % n_copies]
        _trial["i"] += 1
        tensors = []
        for path, sh, nb in zip(ps, shapes, nbytes):
            raw = _read_nocache(path, nb)
            arr = np.frombuffer(raw, dtype=np_dtype).reshape(sh)
            tt = torch.from_numpy(arr.copy()).to(dev, non_blocking=True)
            tensors.append(tt)
        return expert_forward(x, *tensors)

    t_ssd, s_ssd = measure(ssd_miss, dev_type, warmup=2, trials=n_copies)
    print(f"[SSD miss]  read+H2D+compute     : {t_ssd:8.1f} μs  (±{s_ssd:.1f})  [F_NOCACHE cold]")

    # 纯冷读盘成本
    _trial["i"] = 0

    def ssd_read_only():
        ps = copy_paths[_trial["i"] % n_copies]
        _trial["i"] += 1
        return [_read_nocache(path, nb) for path, nb in zip(ps, nbytes)]

    t_ssd_read, _ = measure(ssd_read_only, "cpu", warmup=2, trials=n_copies)
    print(f"            └─ read only         : {t_ssd_read:8.1f} μs"
          f"  (eff BW {esz_mb/1024/(t_ssd_read/1e6):.1f} GB/s, cold NVMe)")

    # cleanup
    for ps in copy_paths:
        for p in ps:
            os.unlink(p)
    os.rmdir(tmpdir)

    print("-" * 68)
    print("Tier latency ratios (relative to HBM hit):")
    print(f"  HBM : 1.00x   ({t_hbm:.0f} μs)")
    print(f"  CPU : {t_cpu/t_hbm:.2f}x   ({t_cpu:.0f} μs)")
    print(f"  SSD : {t_ssd/t_hbm:.2f}x   ({t_ssd:.0f} μs)")
    print("=" * 68)

    result = {
        "device": dev_type,
        "expert_size_mb": round(esz_mb, 1),
        "dtype": args.dtype,
        "token_batch": args.batch,
        "hidden": args.hidden, "ffn": args.ffn,
        "tier_latency_us": {
            "hbm_hit": round(t_hbm, 1),
            "cpu_hit": round(t_cpu, 1),
            "ssd_miss": round(t_ssd, 1),
        },
        "transfer_only_us": {
            "cpu_to_device": round(t_cpu_xfer, 1),
            "ssd_read": round(t_ssd_read, 1),
        },
        "ratios_vs_hbm": {
            "cpu": round(t_cpu / t_hbm, 3),
            "ssd": round(t_ssd / t_hbm, 3),
        },
        "note": "CPU tier uses PINNED (page-locked) host memory — fair vs real "
                "offload systems & avoids pageable 6-7GB/s artifact. SSD read is COLD: "
                "macOS F_NOCACHE / Linux posix_fadvise(DONTNEED). H2D via tensor.to(dev, non_blocking=True).",
    }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Saved → {args.out}")


if __name__ == "__main__":
    main()
