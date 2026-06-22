#!/usr/bin/env python3
"""
MECC Compiler — MoE Expert Cache Compiler
==========================================
输入:  HuggingFace MoE 模型名
输出:  编译结果 (JSON + 报告)

Pipeline:
  Phase 1 — Inspect:  加载模型, 提取结构参数 (n_experts, expert_size, n_layers...)
  Phase 2 — Profile:  用真实输入跑 forward, 从 router_logits 采集 expert 激活分布 → 估算 Zipf α
  Phase 3 — Hardware: 测量当前 GPU 的延迟/带宽参数 (CUDA / MPS / CPU)
  Phase 4 — Compile:  Theorem 4 最优三级分配 (K_H, K_C) → tier_map
  Phase 5 — Emit:     JSON 配置 + 完整编译报告

Usage:
  python compile.py --model mistralai/Mixtral-8x7B-v0.1
  python compile.py --model Qwen/Qwen1.5-MoE-A2.7B
  python compile.py --model mistralai/Mixtral-8x7B-v0.1 --hw a100  # 用预设硬件
"""
import argparse, json, math, os, statistics, sys, time
from collections import Counter
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import torch
import numpy as np


# ═══════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════

@dataclass
class ModelInfo:
    """Phase 1 输出: 模型结构参数"""
    name: str
    n_experts: int            # 总 expert 数 (所有层合计, 或单层)
    n_layers: int             # MoE 层数
    expert_size_mb: float     # 单个 expert 权重大小 (MB)
    hidden_dim: int
    ffn_dim: int
    top_k: int                # 每次激活的 expert 数
    total_params_b: float     # 总参数量 (B)
    dtype: str                # fp16 / bf16 / fp32


@dataclass
class ActivationProfile:
    """Phase 2 输出: expert 激活分布"""
    alpha: float              # Zipf α
    top10_coverage_pct: float # Top-10 expert 覆盖的访问比例
    top50_coverage_pct: float
    n_experts_active: int     # 实际被激活过的 expert 数
    n_tokens_processed: int
    access_counts: List[int]  # 每个 expert 的访问计数
    per_layer_alpha: List[float] = field(default_factory=list)


@dataclass
class HardwareProfile:
    """Phase 3 输出: 硬件延迟/带宽参数"""
    device_type: str          # cuda / mps / cpu
    device_name: str
    architecture: str         # unified / discrete
    gpu_lat_us: float         # GPU 计算 350MB expert 的延迟
    cpu_lat_us: float         # CPU 计算 350MB expert 的延迟
    gpu_bw_gbs: float         # GPU 有效带宽
    ssd_read_us: float        # SSD 读 100MB 延迟
    ssd_write_us: float
    total_memory_gb: float


@dataclass
class CompileResult:
    """Phase 4 输出: 编译结果"""
    model: str
    hardware: str
    alpha: float
    # 结构
    n_experts: int
    expert_size_mb: float
    # 分配
    hbm_slots: int
    cpu_slots: int
    ssd_slots: int
    # 命中率
    hbm_hit_rate: float
    cpu_hit_rate: float
    ssd_hit_rate: float
    # 延迟
    avg_latency_us: float
    vs_fluxmoe_speedup: float
    vs_swapmoe_speedup: float
    # tier map
    tier_map: Dict[str, List[int]] = field(default_factory=dict)
    # 完整中间数据
    model_info: Optional[dict] = None
    profile: Optional[dict] = None
    hardware_profile: Optional[dict] = None


# ═══════════════════════════════════════════════════════════════
# Phase 1: Inspect — 模型结构分析
# ═══════════════════════════════════════════════════════════════

def inspect_model(model_name: str, device: torch.device) -> ModelInfo:
    """加载模型, 提取 MoE 结构参数"""
    from transformers import AutoConfig

    print(f"\n{'─'*60}")
    print(f"[Phase 1] Inspect: {model_name}")
    print(f"{'─'*60}")

    config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)

    # 识别 MoE 参数 (兼容 Mixtral / Qwen-MoE / DeepSeek 等)
    n_layers = getattr(config, "num_hidden_layers",
               getattr(config, "num_layers",
               getattr(config, "n_layer", None)))

    n_experts = getattr(config, "num_local_experts",
                getattr(config, "num_experts",
                getattr(config, "moe_num_experts", None)))

    top_k = getattr(config, "num_experts_per_tok",
            getattr(config, "top_k",
            getattr(config, "moe_top_k", 2)))

    hidden_dim = getattr(config, "hidden_size",
                 getattr(config, "d_model", None))
    ffn_dim = getattr(config, "intermediate_size",
              getattr(config, "ffn_hidden_size",
              getattr(config, "moe_intermediate_size", None)))

    dtype_str = str(getattr(config, "torch_dtype", "float16"))

    # 估算 expert 大小: 2 * hidden * ffn * 2 (gate+up+down, fp16)
    if hidden_dim and ffn_dim:
        expert_params = 3 * hidden_dim * ffn_dim  # gate, up, down
        expert_size_mb = expert_params * 2 / (1024 * 1024)  # fp16 → MB
    else:
        expert_size_mb = 350  # 默认: Mixtral 级别

    # 总参数估算
    if hidden_dim and ffn_dim and n_layers:
        total_params = n_layers * (n_experts * expert_params + 4 * hidden_dim * hidden_dim)
        total_params_b = total_params / 1e9
    else:
        total_params_b = 0

    info = ModelInfo(
        name=model_name,
        n_experts=n_experts or 0,
        n_layers=n_layers or 0,
        expert_size_mb=expert_size_mb,
        hidden_dim=hidden_dim or 0,
        ffn_dim=ffn_dim or 0,
        top_k=top_k or 2,
        total_params_b=total_params_b,
        dtype=dtype_str,
    )

    print(f"  Layers:      {info.n_layers}")
    print(f"  Experts:     {info.n_experts}  (top_k={info.top_k})")
    print(f"  Hidden dim:  {info.hidden_dim}")
    print(f"  FFN dim:     {info.ffn_dim}")
    print(f"  Expert size: {info.expert_size_mb:.1f} MB")
    print(f"  Total params: {info.total_params_b:.1f}B")
    print(f"  Dtype:       {info.dtype}")

    if info.n_experts == 0:
        print(f"  ⚠️  Could not detect MoE config — model may not be MoE!")
        print(f"  Config keys: {list(config.to_dict().keys())[:20]}...")

    return info


# ═══════════════════════════════════════════════════════════════
# Phase 2: Profile — 采集 expert 激活分布
# ═══════════════════════════════════════════════════════════════

def estimate_zipf_alpha(counts: List[int]) -> float:
    """MLE for Zipf α: α ≈ 1 + N / Σ log(rank_i)"""
    n = len(counts)
    if n == 0:
        return 1.0
    log_sum = sum(math.log(max(r, 1)) for r in range(1, n + 1))
    alpha = 1.0 + n / log_sum if log_sum > 0 else 1.0
    return min(max(alpha, 0.5), 3.0)


def profile_activations(model_name: str, model_info: ModelInfo,
                        device: torch.device, n_tokens: int = 1000) -> ActivationProfile:
    """用真实输入跑模型, 从 router_logits 采集 expert 激活"""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"\n{'─'*60}")
    print(f"[Phase 2] Profile: expert activations")
    print(f"{'─'*60}")

    print(f"  Loading model weights ({device.type})...")
    t_load = time.time()

    try:
        if device.type == "cuda":
            model = AutoModelForCausalLM.from_pretrained(
                model_name, torch_dtype=torch.float16, device_map="auto",
                trust_remote_code=True)
        else:
            model = AutoModelForCausalLM.from_pretrained(
                model_name, torch_dtype=torch.float16, trust_remote_code=True).to(device)
    except Exception as e:
        print(f"  ✗ Failed to load model: {e}")
        raise

    print(f"  Loaded in {time.time() - t_load:.1f}s")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

    # 多句 prompt 覆盖不同语义
    prompts = [
        "The capital of France is",
        "Machine learning is a field of",
        "The theory of relativity was developed by",
        "In computer science, a binary tree is",
        "The Great Wall of China was built during",
        "Photosynthesis is the process by which",
        "The Fibonacci sequence is defined as",
        "Quantum mechanics describes the behavior of",
    ]

    n_experts = model_info.n_experts
    expert_activations = Counter()
    per_layer_counts = {}  # layer_idx → Counter

    print(f"  Running {n_tokens} tokens through model...")
    t_prof = time.time()
    n_processed = 0

    with torch.no_grad():
        for prompt in prompts:
            if n_processed >= n_tokens:
                break
            try:
                inputs = tokenizer(prompt, return_tensors="pt").to(device)
                outputs = model(**inputs, output_router_logits=True)

                if hasattr(outputs, "router_logits") and outputs.router_logits:
                    for layer_idx, layer_logits in enumerate(outputs.router_logits):
                        # layer_logits: [batch, seq_len, n_experts]
                        if layer_logits is None:
                            continue
                        topk_vals, topk_ids = layer_logits[0].topk(model_info.top_k, dim=-1)
                        # flatten → Counter.update (避免 Python 逐元素循环)
                        flat_ids = topk_ids.flatten().cpu().tolist()
                        expert_activations.update(flat_ids)
                        if layer_idx not in per_layer_counts:
                            per_layer_counts[layer_idx] = Counter()
                        per_layer_counts[layer_idx].update(flat_ids)
                        n_processed += topk_ids.shape[0] * model_info.top_k

                # 清理
                del outputs, inputs
                if device.type == "mps":
                    torch.mps.empty_cache()

            except Exception as e:
                print(f"  ⚠️  Prompt error: {e}")
                continue

    print(f"  Processed ~{n_processed} expert activations in {time.time() - t_prof:.1f}s")

    # 计算 α
    counts = [expert_activations.get(i, 0) for i in range(n_experts)]
    alpha = estimate_zipf_alpha(counts)

    # 每层 α
    per_layer_alpha = []
    for li in sorted(per_layer_counts.keys()):
        lc = [per_layer_counts[li].get(i, 0) for i in range(n_experts)]
        per_layer_alpha.append(estimate_zipf_alpha(lc))

    sorted_counts = sorted(counts, reverse=True)
    total = sum(counts)
    top10_cov = sum(sorted_counts[:10]) / total * 100 if total else 0
    top50_cov = sum(sorted_counts[:50]) / total * 100 if total else 0
    n_active = sum(1 for c in counts if c > 0)

    profile = ActivationProfile(
        alpha=alpha,
        top10_coverage_pct=top10_cov,
        top50_coverage_pct=top50_cov,
        n_experts_active=n_active,
        n_tokens_processed=n_processed,
        access_counts=counts,
        per_layer_alpha=per_layer_alpha,
    )

    print(f"  α = {alpha:.3f}")
    print(f"  Top-10 coverage: {top10_cov:.1f}%")
    print(f"  Top-50 coverage: {top50_cov:.1f}%")
    print(f"  Active experts:  {n_active}/{n_experts}")
    if per_layer_alpha:
        print(f"  Per-layer α:     [{', '.join(f'{a:.2f}' for a in per_layer_alpha[:5])}"
              f"{'...' if len(per_layer_alpha) > 5 else ''}]")

    # 释放模型
    del model, tokenizer
    if device.type == "mps":
        torch.mps.empty_cache()
    elif device.type == "cuda":
        torch.cuda.empty_cache()

    return profile


# ═══════════════════════════════════════════════════════════════
# Phase 3: Hardware — 表征当前设备
# ═══════════════════════════════════════════════════════════════

def profile_hardware(device: torch.device, expert_size_mb: float = 350) -> HardwareProfile:
    """测量 GPU/CPU/SSD 延迟和带宽"""
    print(f"\n{'─'*60}")
    print(f"[Phase 3] Hardware characterization")
    print(f"{'─'*60}")

    device_type = device.type
    n_warmup, n_trials = 3, 10

    def sync():
        if device_type == "cuda":
            torch.cuda.synchronize()
        elif device_type == "mps":
            torch.mps.synchronize()

    # --- GPU 计算延迟 ---
    expert_elements = int(expert_size_mb * 1024 * 1024 / 2)  # fp16
    gpu_tensor = torch.randn(expert_elements, dtype=torch.float16, device=device)
    sync()
    times = []
    for _ in range(n_warmup + n_trials):
        t0 = time.perf_counter()
        _ = gpu_tensor.sum()
        sync()
        times.append(time.perf_counter() - t0)
    gpu_lat = statistics.median(times[n_warmup:]) * 1e6
    del gpu_tensor

    # --- CPU 计算延迟 ---
    cpu_tensor = torch.randn(expert_elements, dtype=torch.float16)
    times = []
    for _ in range(n_warmup + n_trials):
        t0 = time.perf_counter()
        _ = cpu_tensor.sum()
        times.append(time.perf_counter() - t0)
    cpu_lat = statistics.median(times[n_warmup:]) * 1e6
    del cpu_tensor

    # --- GPU 带宽 ---
    large_mb = 400
    large_elems = large_mb * 1024 * 1024 // 2
    large_gpu = torch.randn(large_elems, dtype=torch.float16, device=device)
    sync()
    times = []
    for _ in range(n_warmup + n_trials):
        t0 = time.perf_counter()
        _ = large_gpu.mean()
        sync()
        times.append(time.perf_counter() - t0)
    large_lat = statistics.median(times[n_warmup:]) * 1e6
    gpu_bw = (large_mb / 1e3) / (large_lat / 1e6) if large_lat > 0 else 0
    del large_gpu
    if device_type == "mps":
        torch.mps.empty_cache()

    # --- SSD 延迟 ---
    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        data = torch.randn(50 * 1024 * 1024, dtype=torch.float16)
        raw = data.numpy().tobytes()
        times = []
        for _ in range(n_trials):
            t0 = time.perf_counter()
            tmp.write(raw); tmp.flush()
            os.fsync(tmp.fileno())
            times.append(time.perf_counter() - t0)
        ssd_write = statistics.median(times) * 1e6

        tmp.seek(0)
        times = []
        for _ in range(n_trials):
            t0 = time.perf_counter()
            tmp.seek(0)
            _ = tmp.read()
            times.append(time.perf_counter() - t0)
        ssd_read = statistics.median(times) * 1e6
    finally:
        tmp.close()
        os.unlink(tmp.name)

    # --- 内存总量 ---
    if device_type == "mps":
        import subprocess
        try:
            r = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
            total_mem = int(r.stdout.strip()) / 1e9
        except:
            total_mem = 52
    elif device_type == "cuda":
        total_mem = torch.cuda.get_device_properties(0).total_mem / 1e9
    else:
        total_mem = 0

    # 架构判断
    arch = "unified" if device_type == "mps" else "discrete"

    hw = HardwareProfile(
        device_type=device_type,
        device_name="Apple MPS" if device_type == "mps" else
                     torch.cuda.get_device_name(0) if device_type == "cuda" else "CPU",
        architecture=arch,
        gpu_lat_us=gpu_lat,
        cpu_lat_us=cpu_lat,
        gpu_bw_gbs=gpu_bw,
        ssd_read_us=ssd_read,
        ssd_write_us=ssd_write,
        total_memory_gb=total_mem,
    )

    print(f"  Device:       {hw.device_name} ({device_type})")
    print(f"  Architecture: {arch}")
    print(f"  Total memory: {hw.total_memory_gb:.0f} GB")
    print(f"  GPU lat:      {gpu_lat:.0f} μs  (for {expert_size_mb:.0f}MB expert)")
    print(f"  CPU lat:      {cpu_lat:.0f} μs")
    print(f"  GPU BW:       {gpu_bw:.0f} GB/s")
    print(f"  SSD read:     {ssd_read:.0f} μs")
    print(f"  SSD write:    {ssd_write:.0f} μs")

    return hw


# ═══════════════════════════════════════════════════════════════
# Phase 4: Compile — 最优三级分配
# ═══════════════════════════════════════════════════════════════

def zipf_cdf(k: int, N: int, alpha: float) -> float:
    """Zipf CDF: 前 k 个 expert 的累积命中率 (调和数缓存, numpy 向量化)"""
    if k >= N:
        return 1.0
    if k <= 0:
        return 0.0
    hn = _harmonic_n(N, alpha)
    hk = _harmonic_n(k, alpha)
    return hk / hn if hn > 0 else 0.0


@lru_cache(maxsize=128)
def _harmonic_n(n: int, alpha: float) -> float:
    """缓存 N 的调和数, 避免 zipf_cdf 重复 O(N) 计算"""
    return float(np.sum(1.0 / np.arange(1, n + 1, dtype=np.float64) ** float(alpha)))


def compile_tiers(model_info: ModelInfo, profile: ActivationProfile,
                  hw: HardwareProfile) -> CompileResult:
    """Theorem 4: 计算最优 (K_H, K_C) 三级分配"""
    print(f"\n{'─'*60}")
    print(f"[Phase 4] Compile: tier allocation")
    print(f"{'─'*60}")

    alpha = profile.alpha
    esz_gb = model_info.expert_size_mb / 1024
    N = model_info.n_experts

    # 可用槽位
    # GPU 这边: 留 20% 给 KV cache 和其他
    usable_gpu_gb = hw.total_memory_gb * 0.6
    K_H = min(int(usable_gpu_gb / esz_gb), N)

    # CPU: 假设可用 80% 系统内存 (统一内存架构下共享)
    cpu_usable_gb = hw.total_memory_gb * 0.6
    K_C = min(int(cpu_usable_gb / esz_gb), N - K_H)

    # 延迟
    T_H = hw.gpu_lat_us
    T_C = hw.cpu_lat_us
    T_S = hw.ssd_read_us

    # 命中率
    hbm_hit = zipf_cdf(K_H, N, alpha)
    cpu_hit = zipf_cdf(K_H + K_C, N, alpha) - hbm_hit
    ssd_hit = 1.0 - hbm_hit - cpu_hit

    avg_lat = T_H * hbm_hit + T_C * cpu_hit + T_S * ssd_hit

    # Baselines
    flux_lat = T_C                               # FluxMoE: 总是从 CPU 加载
    swap_hbm_slots = int(usable_gpu_gb / esz_gb)
    swap_hbm_hit = zipf_cdf(swap_hbm_slots, N, alpha)
    swap_lat = T_H * swap_hbm_hit + T_S * (1 - swap_hbm_hit)  # SwapMoE: HBM+SSD

    # tier map
    tier_map = {
        "hbm": list(range(K_H)),
        "cpu": list(range(K_H, K_H + K_C)),
        "ssd": list(range(K_H + K_C, N)),
    }

    result = CompileResult(
        model=model_info.name,
        hardware=hw.device_name,
        alpha=alpha,
        n_experts=N,
        expert_size_mb=model_info.expert_size_mb,
        hbm_slots=K_H,
        cpu_slots=K_C,
        ssd_slots=N - K_H - K_C,
        hbm_hit_rate=hbm_hit * 100,
        cpu_hit_rate=cpu_hit * 100,
        ssd_hit_rate=ssd_hit * 100,
        avg_latency_us=avg_lat,
        vs_fluxmoe_speedup=flux_lat / avg_lat if avg_lat > 0 else 0,
        vs_swapmoe_speedup=swap_lat / avg_lat if avg_lat > 0 else 0,
        tier_map=tier_map,
        model_info=asdict(model_info),
        profile={
            "alpha": alpha,
            "top10_coverage": profile.top10_coverage_pct,
            "top50_coverage": profile.top50_coverage_pct,
            "n_active": profile.n_experts_active,
            "per_layer_alpha": profile.per_layer_alpha,
        },
        hardware_profile=asdict(hw),
    )

    # 打印
    def fmt_range(lst):
        if not lst: return "[]"
        rng = []
        start = lst[0]; end = lst[0]
        for v in lst[1:]:
            if v == end + 1:
                end = v
            else:
                rng.append(f"{start}" if start == end else f"{start}..{end}")
                start = end = v
        rng.append(f"{start}" if start == end else f"{start}..{end}")
        return "[" + ",".join(rng) + "]"

    print(f"  α = {alpha:.3f}")
    print(f"")
    print(f"  Tier   Slots      Hit%        Latency")
    print(f"  ─────  ─────      ────        ───────")
    print(f"  HBM    {K_H:<10} {hbm_hit*100:>5.1f}%       {T_H:.0f} μs")
    print(f"  CPU    {K_C:<10} {cpu_hit*100:>5.1f}%       {T_C:.0f} μs")
    print(f"  SSD    {N-K_H-K_C:<10} {ssd_hit*100:>5.1f}%       {T_S:.0f} μs")
    print(f"")
    print(f"  Avg latency: {avg_lat:.0f} μs")
    print(f"  vs FluxMoE:  {result.vs_fluxmoe_speedup:.1f}×")
    print(f"  vs SwapMoE:  {result.vs_swapmoe_speedup:.1f}×")
    print(f"")
    print(f"  Tier map:")
    print(f"    HBM: {fmt_range(tier_map['hbm'])}")
    print(f"    CPU: {fmt_range(tier_map['cpu'])}")
    print(f"    SSD: {fmt_range(tier_map['ssd'])}")

    return result


# ═══════════════════════════════════════════════════════════════
# Phase 5: Emit — 输出 JSON
# ═══════════════════════════════════════════════════════════════

def emit(result: CompileResult, output_dir: str = "."):
    """输出完整编译结果 (JSON + 报告)"""
    print(f"\n{'─'*60}")
    print(f"[Phase 5] Emit")
    print(f"{'─'*60}")

    safe_name = result.model.replace("/", "_")
    json_path = os.path.join(output_dir, f"{safe_name}_compile.json")

    output = asdict(result)
    # tier_map 压缩显示
    compressed = dict(output)
    compressed["tier_map"] = {
        k: f"[{v[0]}..{v[-1]}]" if len(v) > 2 else str(v)
        for k, v in result.tier_map.items()
    }
    compressed["model_info"] = result.model_info
    compressed["profile"] = result.profile
    compressed["hardware_profile"] = result.hardware_profile

    with open(json_path, "w") as f:
        json.dump(compressed, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Saved to {json_path}")
    print(f"  File size: {os.path.getsize(json_path)} bytes")

    return json_path


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def get_device() -> Tuple[torch.device, str]:
    if torch.cuda.is_available():
        return torch.device("cuda"), "CUDA"
    elif torch.backends.mps.is_available():
        return torch.device("mps"), "MPS (Apple GPU)"
    else:
        return torch.device("cpu"), "CPU"


def compile_model(model_name: str, hw_profile: Optional[HardwareProfile] = None,
                  output_dir: str = ".") -> CompileResult:
    """完整编译 pipeline"""

    print("=" * 60)
    print("MECC Compiler — MoE Expert Cache Compiler")
    print("=" * 60)
    print(f"Model:    {model_name}")
    t_start = time.time()

    device, dev_name = get_device()
    print(f"Device:   {dev_name}")

    # Phase 1: Inspect
    model_info = inspect_model(model_name, device)

    # Phase 2: Profile
    profile_result = profile_activations(model_name, model_info, device)

    # Phase 3: Hardware
    if hw_profile is None:
        hw_result = profile_hardware(device, model_info.expert_size_mb)
    else:
        hw_result = hw_profile

    # Phase 4: Compile
    config = compile_tiers(model_info, profile_result, hw_result)

    # Phase 5: Emit
    json_path = emit(config, output_dir)

    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"Compilation complete in {elapsed:.0f}s")
    print(f"Output: {json_path}")
    print(f"{'='*60}")

    return config


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MECC Compiler")
    parser.add_argument("--model", type=str, default="mistralai/Mixtral-8x7B-v0.1",
                        help="HuggingFace MoE model name")
    parser.add_argument("--output", type=str, default=".",
                        help="Output directory for JSON")
    args = parser.parse_args()

    compile_model(args.model, output_dir=args.output)
