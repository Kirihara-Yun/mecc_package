#!/usr/bin/env python3
"""
MECC GPU Profiling — 支持 CUDA / Apple MPS
============================================
三步验证: α值 → 延迟参数 → 端到端
"""
import sys, time, json, statistics, math, os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from compiler import estimate_alpha as _compiler_estimate_alpha


def get_device():
    """自动检测最佳设备: CUDA > MPS > CPU"""
    import torch
    if torch.cuda.is_available():
        return torch.device("cuda"), "CUDA"
    elif torch.backends.mps.is_available():
        return torch.device("mps"), "MPS (Apple GPU)"
    else:
        return torch.device("cpu"), "CPU"


# ═══════════════════════════════════════════════════════════
# Step 1: 测 Expert 激活分布 (估算 Zipf α)
# ═══════════════════════════════════════════════════════════

def profile_alpha(model_name="mistralai/Mixtral-8x7B-v0.1", n_samples=1000):
    """估算 Zipf α — MPS 上用模拟 (避免大模型下载), CUDA 上真实 profile"""
    print(f"\n[Step 1] Profiling α...")
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device, dev_name = get_device()
        print(f"  Device: {dev_name}")

        if device.type == "mps":
            # MPS: 轻量 smoke test + 模拟 α
            print(f"  Apple MPS: skipping large model download, using known α range")
            try:
                smoke_model = "HuggingFaceTB/SmolLM2-135M-Instruct"
                print(f"  Smoke test with {smoke_model}...")
                smoke_tok = AutoTokenizer.from_pretrained(smoke_model)
                smoke_m = AutoModelForCausalLM.from_pretrained(
                    smoke_model, torch_dtype=torch.float16).to(device)
                prompt = "The capital of France is"
                smoke_in = smoke_tok(prompt, return_tensors="pt").to(device)
                with torch.no_grad():
                    _ = smoke_m(**smoke_in)
                print(f"  ✓ MPS GPU forward OK!")
                del smoke_m, smoke_tok, smoke_in
                torch.mps.empty_cache()
            except Exception as e:
                print(f"  ⚠️  MPS smoke test failed: {e}")

            # 使用文献已知 α ≈ 1.2 (Zipf in MoE)
            import random; random.seed(42)
            N = 256; true_alpha = 1.2
            w = [1.0/i**true_alpha for i in range(1, N+1)]
            probs = [x/sum(w) for x in w]
            access_counts = [0]*N
            for _ in range(n_samples * 10):
                access_counts[random.choices(range(N), weights=probs, k=1)[0]] += 1
            estimated_alpha = estimate_alpha(access_counts)
            return {"estimated_alpha": estimated_alpha, "n_experts": N,
                    "method": f"MPS smoke OK + simulated (Zipf α={true_alpha})"}

        elif device.type == "cuda":
            print(f"  Loading {model_name}...")
            model = AutoModelForCausalLM.from_pretrained(
                model_name, torch_dtype=torch.float16, device_map="auto")
            tokenizer = AutoTokenizer.from_pretrained(model_name)

            expert_activations = Counter()
            prompt = "The capital of France is"
            inputs = tokenizer(prompt, return_tensors="pt").to(device)

            with torch.no_grad():
                outputs = model(**inputs, output_router_logits=True)
                if hasattr(outputs, "router_logits") and outputs.router_logits:
                    for layer_logits in outputs.router_logits:
                        top2 = layer_logits[0].topk(2).indices.flatten().tolist()
                        for eid in top2:
                            expert_activations[eid] += 1

            counts = [expert_activations.get(i, 0) for i in range(256)]
            alpha = estimate_alpha(counts)
            return {"estimated_alpha": alpha, "n_experts": 256,
                    "method": "CUDA (transformers)",
                    "access_counts": counts[:20]}

        # 回退: 模拟
        import random; random.seed(42)
        N = 256; true_alpha = 1.2
        w = [1.0/i**true_alpha for i in range(1, N+1)]
        probs = [x/sum(w) for x in w]
        access_counts = [0]*N
        for _ in range(n_samples * 10):
            access_counts[random.choices(range(N), weights=probs, k=1)[0]] += 1
        estimated_alpha = estimate_alpha(access_counts)
        return {"estimated_alpha": estimated_alpha, "n_experts": N,
                "method": f"simulated (Zipf α={true_alpha})"}

    except ImportError as e:
        print(f"  ⚠️  Import error: {e}. Using simulated data.")
        import random; random.seed(42)
        N = 256; true_alpha = 1.2
        w = [1.0/i**true_alpha for i in range(1, N+1)]
        probs = [x/sum(w) for x in w]
        counts = [0]*N
        for _ in range(n_samples * 10):
            counts[random.choices(range(N), weights=probs, k=1)[0]] += 1
        return {"estimated_alpha": estimate_alpha(counts), "n_experts": N,
                "method": "simulated (no transformers)"}


def estimate_alpha(counts):
    """Use the compiler's bounded discrete-Zipf MLE implementation."""
    return _compiler_estimate_alpha(counts)


# ═══════════════════════════════════════════════════════════
# Step 2: 测 统一内存 / SSD 延迟参数
# ═══════════════════════════════════════════════════════════

def profile_latency():
    """测量 GPU 计算 / 统一内存带宽 / SSD 读取延迟, 校准模拟器参数
    
    Apple Silicon 统一内存架构:
    - CPU 和 GPU 共享同一物理内存, 无传统 H2D/D2H 拷贝
    - 「GPU latency」≈ MPS kernel launch + 计算时间
    - 「CPU latency」≈ CPU tensor 计算时间 (可视为"冷路径")
    - SSD: 仍然是最慢层 (macOS swap / 显式 NVMe 读)
    """
    print(f"\n[Step 2] Profiling latency parameters...")
    try:
        import torch
        device, dev_name = get_device()

        expert_size_bytes = 350 * 1024 * 1024  # 350MB (典型 expert 大小)
        expert_elements = expert_size_bytes // 2  # fp16 元素数
        n_warmup, n_trials = 3, 10
        
        def sync():
            if device.type == "cuda":
                torch.cuda.synchronize()
            elif device.type == "mps":
                torch.mps.synchronize()

        # --- A. GPU 计算延迟 (MPS/CUDA tensor op) ---
        gpu_tensor = torch.randn(expert_elements, dtype=torch.float16, device=device)
        sync()
        times = []
        for _ in range(n_warmup + n_trials):
            t0 = time.perf_counter()
            _ = gpu_tensor.sum()
            sync()
            times.append(time.perf_counter() - t0)
        gpu_lat = statistics.median(times[n_warmup:]) * 1e6

        # --- B. CPU tensor 计算延迟 (作为对比) ---
        cpu_tensor = torch.randn(expert_elements, dtype=torch.float16)
        times = []
        for _ in range(n_warmup + n_trials):
            t0 = time.perf_counter()
            _ = cpu_tensor.sum()
            times.append(time.perf_counter() - t0)
        cpu_lat = statistics.median(times[n_warmup:]) * 1e6

        # --- C. 统一内存带宽: GPU 读大块数据 ---
        # Apple Silicon: CPU↔GPU 零拷贝, 但 GPU 访问统一内存有带宽限制
        large_gpu = torch.randn(200 * 1024 * 1024, dtype=torch.float16, device=device)  # 400MB
        sync()
        times = []
        for _ in range(n_warmup + n_trials):
            t0 = time.perf_counter()
            _ = large_gpu.mean()
            sync()
            times.append(time.perf_counter() - t0)
        large_gpu_lat = statistics.median(times[n_warmup:]) * 1e6
        # 估算有效带宽 (GB/s)
        ef_bw = (400 / 1e3) / (large_gpu_lat / 1e6) if large_gpu_lat > 0 else 0  # GB/ms → GB/s
        del large_gpu; 
        if device.type == "mps":
            torch.mps.empty_cache()

        # --- D. SSD 延迟: 写入+读取临时文件 (模拟 NVMe) ---
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            data = torch.randn(50 * 1024 * 1024, dtype=torch.float16)  # 100MB
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

        # 组装结果: Apple Silicon 上 "CPU latency" ≈ CPU tensor 计算
        # 因为无 H2D 拷贝, 统一内存中 CPU 和 GPU 访问同一数据
        result = {
            "gpu_lat_us": gpu_lat,         # GPU 计算延迟
            "cpu_lat_us": cpu_lat,         # CPU 计算延迟
            "gpu_bw_gbs": ef_bw,           # 有效 GPU 带宽
            "ssd_read_us": ssd_read,       # SSD 读延迟
            "ssd_write_us": ssd_write,     # SSD 写延迟
            "method": f"{dev_name} measured",
            "expert_size_mb": expert_size_bytes // (1024*1024),
            "architecture": "unified" if device.type == "mps" else "discrete",
        }
        return result

    except ImportError:
        print("  ⚠️  torch not installed! Using theoretical values.")
        return {"gpu_lat_us": 176, "cpu_lat_us": 3510, "gpu_bw_gbs": 2000,
                "ssd_read_us": 50000, "ssd_write_us": 50000,
                "method": "theoretical", "architecture": "unknown"}


# ═══════════════════════════════════════════════════════════
# Step 3: 端到端验证
# ═══════════════════════════════════════════════════════════

def run_end_to_end(alpha, lat_result):
    """用校准参数运行完整 benchmark"""
    print(f"\n[Step 3] End-to-end benchmark with calibrated parameters...")
    
    from tiered_cache import benchmark, report_cache, e2e_throughput, report_e2e

    gpu_lat = lat_result.get("gpu_lat_us", 176)
    cpu_lat = lat_result.get("cpu_lat_us", 3510)
    ssd_lat = lat_result.get("ssd_read_us", 50000)
    arch = lat_result.get("architecture", "unknown")
    gpu_bw = lat_result.get("gpu_bw_gbs", 2000)

    print(f"  Architecture: {arch}")
    print(f"  α={alpha:.2f}  GPU={gpu_lat:.0f}μs  CPU={cpu_lat:.0f}μs  SSD={ssd_lat:.0f}μs  BW={gpu_bw:.0f}GB/s")

    # Cache hit rate benchmark
    bms = [benchmark("mixtral-8x7b", "a100", alpha)]
    report_cache(bms)

    # Throughput (使用 A100 规格, Apple Silicon 上研究三级缓存可行性)
    for model in ["mixtral-8x7b", "large-moe"]:
        print(f"\n  End-to-end ({model}):")
        for seq in [2048, 4096, 8192]:
            for batch in [4, 8, 16]:
                kv = batch * 2 * seq * 32 * 4096 * 2 / 1e9
                hbm_left = 40 - kv
                if hbm_left < 1: continue
                t = e2e_throughput(batch, seq, hbm_left, model, "a100")
                sp = t["TieredLRU"] / t["SwapMoE"] if t["SwapMoE"] > 0 else 0
                m = " ★" if sp > 1.5 else (" ✓" if sp > 1.2 else "")
                print(f"    seq={seq} b={batch}  "
                      f"Flux={t['FluxMoE']:.3f} Swap={t['SwapMoE']:.3f} "
                      f"TLR={t['TieredLRU']:.3f} sp={sp:.1f}x{m}")

    # Apple Silicon 特化分析
    if arch == "unified":
        print(f"\n  [Apple Silicon Analysis]")
        print(f"    统一内存: CPU↔GPU 无拷贝开销, GPU计算={gpu_lat:.0f}μs vs CPU={cpu_lat:.0f}μs")
        print(f"    有效GPU带宽: {gpu_bw:.0f} GB/s (vs A100 HBM: 2000 GB/s)")
        if gpu_bw > 0:
            ratio = gpu_lat / cpu_lat if cpu_lat > 0 else 0
            print(f"    GPU/CPU 加速比: {ratio:.1f}x (A100 HBM/CPU ≈ 0.05x)")
            print(f"    → Apple Silicon 上「近存计算」优势明显, 三级缓存中的 SSD 层更重要")


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("MECC GPU Profiling")
    print("=" * 60)
    
    # 系统信息
    import torch
    device, dev_name = get_device()
    print(f"Device: {dev_name}")
    if device.type == "mps":
        print(f"PyTorch: {torch.__version__}  |  MPS: OK")
        # 获取统一内存大小
        import subprocess
        try:
            mem = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
            mem_gb = int(mem.stdout.strip()) / 1e9
            print(f"Unified Memory: {mem_gb:.0f} GB")
        except:
            pass

    # Step 1: α
    alpha_result = profile_alpha()
    alpha = alpha_result["estimated_alpha"]
    print(f"\n  → α = {alpha:.2f} (method: {alpha_result['method']})")

    # Step 2: Latency
    lat_result = profile_latency()
    print(f"\n  → GPU compute: {lat_result['gpu_lat_us']:.0f}μs")
    print(f"  → CPU compute: {lat_result['cpu_lat_us']:.0f}μs")
    print(f"  → GPU bandwidth: {lat_result.get('gpu_bw_gbs', 0):.0f} GB/s")
    print(f"  → SSD read: {lat_result['ssd_read_us']:.0f}μs  write: {lat_result.get('ssd_write_us', 0):.0f}μs")
    print(f"  → Architecture: {lat_result.get('architecture', 'unknown')}")

    # Step 3: Run
    run_end_to_end(alpha, lat_result)

    print(f"\n{'='*60}")
    print("Profiling complete! 将这些参数填入 compiler.py 的 HardwareSpec")
    print("=" * 60)
