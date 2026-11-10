#!/usr/bin/env python3
"""
run_e2e.py — 真实 MoE 端到端"编译→运行" harness (DAC 主表生成器)
================================================================
与 SOTA (SwapMoE / Fiddler / Mixtral-offloading / MoE-Infinity) **同口径**的实验:
  主指标: TTFT (prefill 首 token) · TPOT (decode 每 token) · throughput (tokens/s)
  精度:   PPL on WikiText-2  ← 我们 = exact/lossless, 对手有损会掉点
  四策略跑在**同一份真实模型 + 同一批 prompt + 同一张卡**上, apples-to-apples。

编译: compile_config.compile_plan() 由 (模型 + 5090 预算 + profiled α) 产出每层 (K_H,K_C)。
运行: 复用 mixtral-offloading 框架 (见 mixtral_tiered.py) 加载真实 Mixtral, 三级缓存 forward。

用法:
  # 0) 本机自检 (不下载, CPU, 秒级) —— 先跑这个确认逻辑通
  python run_e2e.py --smoke

  # 1) 5090 上: 先下载模型 (见 README_E2E.md), 再一键四策略主表
  python run_e2e.py --model mistralai/Mixtral-8x7B-Instruct-v0.1 \
      --state_path /data/mixtral --store_root /data/mecc_store \
      --hbm_budget 22 --cpu_budget 40 --alpha 1.0 \
      --max_new_tokens 64 --n_prompts 8 --out main_table_5090.json
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
import math
import os
import statistics
import time
from typing import List, Optional

import torch
import torch.nn.functional as F

from compile_config import compile_plan, print_plan, MODEL_SPECS, MODEL_TYPE
from tiered_engine import SSDExpertStore
import mixtral_tiered as MT
import deepseek_tiered as DT
from store_manifest import (expected_manifest, validate_store, write_manifest,
                            write_pending_manifest)
from result_schema import atomic_write_result
from offline_inputs import load_manifest, select_prompts, select_ppl_text, GSM8K_PROMPTS

POLICIES = ["ours", "swapmoe", "fiddler", "naive", "flashmoe_rf_adaptation"]

# Insight II: 缓存更新规则 → 具体策略名（冻结初始放置等其他变量时切换）。
# joint=联合更新(ours) / independent=独立更新 / fixed_cpu=固定 CPU(swapmoe 的 static_cpu 语义)
UPDATE_RULE_TO_POLICY = {
    "joint": "ours",
    "independent": "independent",
    "fixed_cpu": "swapmoe",
}


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def sync(device):
    if device.type == "cuda":
        torch.cuda.synchronize()
    elif device.type == "mps":
        torch.mps.synchronize()


# ════════════════════════════════════════════════════════════════════
# 统一前向 (兼容 HF 模型与 smoke TinyMoE)
# ════════════════════════════════════════════════════════════════════

def _forward(model, ids, past, use_cache, use_amp=False):
    amp_ctx = torch.cuda.amp.autocast if (use_amp and torch.cuda.is_available()) else nullcontext
    with amp_ctx():
        if use_cache:
            out = model(ids, past_key_values=past, use_cache=True)
            return out.logits, out.past_key_values
        out = model(ids)
        logits = out.logits if hasattr(out, "logits") else out
        return logits, None

from contextlib import nullcontext


# ════════════════════════════════════════════════════════════════════
# 端到端计时: TTFT (prefill) + TPOT (decode) + tokens/s
# ════════════════════════════════════════════════════════════════════

@torch.no_grad()
def measure_latency(model, input_ids, max_new_tokens, device, use_cache, use_amp=False,
                    trace_fn=None, phase_cb=None):
    sync(device)
    # ---- prefill: 首 token (TTFT) ----
    if phase_cb is not None:
        phase_cb("prefill")
    if trace_fn is not None:
        torch.cuda.reset_peak_memory_stats(device)
    t0 = time.perf_counter()
    try:
        logits, past = _forward(model, input_ids, None, use_cache, use_amp=use_amp)
    except torch.cuda.OutOfMemoryError:
        if trace_fn is not None:
            trace_fn("oom_prefill", 0, None)
        raise
    next_tok = logits[:, -1].argmax(-1, keepdim=True)
    sync(device)
    ttft = time.perf_counter() - t0
    if trace_fn is not None:
        trace_fn("prefill", 0, ttft)

    # ---- decode: 后续每 token (TPOT) ----
    if phase_cb is not None:
        phase_cb("decode")
    step_times = []
    seq = input_ids
    for step in range(1, max_new_tokens):
        if trace_fn is not None:
            torch.cuda.reset_peak_memory_stats(device)
        t0 = time.perf_counter()
        try:
            if use_cache:
                logits, past = _forward(model, next_tok, past, True, use_amp=use_amp)
            else:
                seq = torch.cat([seq, next_tok], dim=1)
                logits, _ = _forward(model, seq, None, False, use_amp=use_amp)
        except torch.cuda.OutOfMemoryError:
            if trace_fn is not None:
                trace_fn("oom_decode", step, None)
            raise
        next_tok = logits[:, -1].argmax(-1, keepdim=True)
        sync(device)
        elapsed = time.perf_counter() - t0
        step_times.append(elapsed)
        if trace_fn is not None:
            trace_fn("decode", step, elapsed)

    tpot = statistics.mean(step_times) if step_times else ttft
    total = ttft + sum(step_times)
    return {"ttft_ms": ttft * 1e3, "tpot_ms": tpot * 1e3,
            "total_s": total, "tokens_per_s": max_new_tokens / total}


def cache_memory_snapshot(caches):
    """Count live expert tensor references by tier for an opt-in diagnostic trace."""
    totals = {"gpu_pool_bytes": 0, "gpu_prefetch_bytes": 0,
              "gpu_nearmiss_bytes": 0, "cpu_nearmiss_bytes": 0,
              "nearmiss_entries": 0, "prefetch_entries": 0}
    for cache in caches:
        if cache is None:
            continue
        totals["gpu_pool_bytes"] += sum(ws.nbytes() for ws, _ in cache.gpu.values())
        pending = getattr(cache, "_prefetch_buf", {})
        totals["prefetch_entries"] += len(pending)
        totals["gpu_prefetch_bytes"] += sum(
            ws.nbytes() for ws in pending.values() if ws.w1.device.type == "cuda")
        near = getattr(cache, "_nearmiss_buf", {})
        totals["nearmiss_entries"] += len(near)
        for ws in near.values():
            key = "gpu_nearmiss_bytes" if ws.w1.device.type == "cuda" else "cpu_nearmiss_bytes"
            totals[key] += ws.nbytes()
    return totals


# ════════════════════════════════════════════════════════════════════
# PPL (teacher forcing) —— 证明无损; 所有 exact 策略 PPL 一致
# ════════════════════════════════════════════════════════════════════

@torch.no_grad()
def measure_ppl(model, tokenizer, text, max_tokens, device, use_cache) -> Optional[float]:
    if tokenizer is None:
        return None
    ids = tokenizer(text, return_tensors="pt").input_ids[:, :max_tokens].to(device)
    if ids.shape[1] < 2:
        return None
    logits, _ = _forward(model, ids, None, False)
    shift_logits = logits[:, :-1].float().reshape(-1, logits.size(-1))
    shift_labels = ids[:, 1:].reshape(-1)
    loss = F.cross_entropy(shift_logits, shift_labels)
    return float(math.exp(loss.item()))


# ════════════════════════════════════════════════════════════════════
# 负载: WikiText-2 prompts (SOTA 标准), 失败则用内置多领域 prompt
# ════════════════════════════════════════════════════════════════════

BUILTIN_PROMPTS = [
    "The economic policy of the central bank affects inflation rates because",
    "In quantum mechanics, entanglement is a phenomenon where",
    "The history of the Roman Empire can be summarized as",
    "To optimize a deep neural network, engineers typically",
    "Climate change impacts coastal cities through",
    "The recipe for a classic French omelette requires",
    "Machine learning models learn from data by",
    "The Renaissance period in Europe was characterized by",
]


def load_prompts(n_prompts: int, max_len: int = 64,
                 use_wikitext: bool = True, manifest=None) -> (List[str], str):
    """返回 (prompts, ppl_text)。优先从离线 manifest 读；否则加载 WikiText-2 test split。

    铁律：WikiText-2 下载/读取失败时**抛异常退出，绝不静默回退**到内置 prompt——
    否则同一批实验会出现「77-token 回退 vs 真实 WikiText-2」的 PPL 输入口径分裂（见 PROVENANCE X13）。
    """
    if manifest is not None:
        # 离线清单：QA 评估 prompt + 固定 PPL 文本；失败即抛异常，不静默回退。
        return select_prompts(manifest, "qa", n_prompts), select_ppl_text(manifest)
    if not use_wikitext:
        # 显式 --skip_ppl：PPL 不参与，prompts 用内置即可（不影响质量口径）。
        return BUILTIN_PROMPTS[:n_prompts], " ".join(BUILTIN_PROMPTS)
    from datasets import load_dataset
    ds = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
    lines = [t.strip() for t in ds["text"] if len(t.strip()) > 80]
    if not lines:
        raise RuntimeError("WikiText-2 test split is empty after filtering; refusing to fall back to builtin prompts")
    return lines[:n_prompts], "\n\n".join(lines[:64])


def organize_task_sequence(prompts: List[str], task_seq: str,
                           task_b_prompts: Optional[List[str]] = None
                           ) -> Tuple[List[str], List[int]]:
    """Motivation III: 按真实任务切换序列组织 prompts。

    task A = prompts（评估输入，如 WikiText-2 前 N 条）
    task B = task_b_prompts（切换目标，如 GSM8K）
    返回 (ordered_prompts, window_sizes)：
      - a_b: A→B（WikiText-2 → GSM8K）
      - b_a: B→A（GSM8K → WikiText-2）
      - a_a: A→A（no-shift 对照，两段相同任务）
      - none: 单窗口（原顺序）

    铁律：a_b/b_a 必须用真实任务 B（GSM8K），拒绝把同一组 WikiText-2 切成前后半
    冒充任务切换（那只是同一任务的两个片段，不构成 A→B）。
    """
    n = len(prompts)
    if task_seq == "none" or n < 2:
        return list(prompts), [n]
    if task_seq == "a_a":
        # no-shift 对照：A→A，两段相同任务，用于区分「缓存漂移」与「自然抖动」
        half = max(1, n // 2)
        return list(prompts[:half]) + list(prompts[:half]), [half, half]
    # a_b / b_a 需要真实任务 B（GSM8K）
    if not task_b_prompts:
        raise ValueError(
            f"task_seq={task_seq} 需要 task_b_prompts（GSM8K 任务 B），"
            f"但未提供；拒绝把同一组 WikiText-2 切成前后半冒充任务切换")
    m = min(len(task_b_prompts), n)
    A = list(prompts[:m])
    B = list(task_b_prompts[:m])
    if task_seq == "a_b":
        return A + B, [len(A), len(B)]
    if task_seq == "b_a":
        return B + A, [len(B), len(A)]
    return list(prompts), [n]


# ════════════════════════════════════════════════════════════════════
# 块设备物理读字节采样（口径核对）
#
# `io_bytes.ssd_read`（tiered_engine.record_hit 累计）是「应用请求字节」：
# miss 次数 × expert 大小，属逻辑口径，未考虑块对齐/RAID 条带/页缓存命中。
# 这里补两个实测口径供核对：
#   * disk_read_bytes —— /proc/diskstats 的 sectors_read×512，块设备层实际读字节（不含页缓存命中）；
#   * proc_read_bytes —— /proc/self/io 的 read_bytes，归属于该进程的存储读取字节；不含纯页缓存命中。
#     /proc/self/io 的 rchar 才是包含缓存命中的逻辑 read 字节（也可能含其他文件）。
# 两者在 run 前后各采样一次，差值随 result 落盘，与 ssd_read 并列对照。
# ════════════════════════════════════════════════════════════════════

def _store_device_name(store_root):
    """解析 store_root 所在块设备名（如 sdb）；失败返回 None。"""
    try:
        import subprocess
        out = subprocess.check_output(
            ["findmnt", "-n", "-o", "SOURCE", "-T", str(store_root)],
            text=True, stderr=subprocess.DEVNULL).strip()
        name = out.split("/")[-1]
        return name or None
    except Exception:
        return None


def _disk_sectors_read(dev):
    """返回 /proc/diskstats 中 dev 的累计 sectors_read×512。"""
    if not dev:
        return 0
    try:
        with open("/proc/diskstats") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 6 and parts[2] == dev:
                    return int(parts[5]) * 512
    except OSError:
        pass
    return 0


def _proc_read_bytes():
    """返回 /proc/self/io 的 read_bytes。"""
    try:
        with open("/proc/self/io") as f:
            for line in f:
                if line.startswith("read_bytes:"):
                    return int(line.split(":")[1].strip())
    except OSError:
        pass
    return 0


# ════════════════════════════════════════════════════════════════════
# 主流程
# ════════════════════════════════════════════════════════════════════

def resolve_state_path(model_name: str, state_path: Optional[str]) -> str:
    if state_path:
        return state_path
    from huggingface_hub import snapshot_download
    print(f"  [hf] snapshot_download({model_name}) ...")
    return snapshot_download(model_name, allow_patterns=[
        "*.safetensors", "*.json", "*.model", "tokenizer*"])


def run_policy(policy, args, plan, store, device, prompts, ppl_text, tokenizer, use_cache,
               smoke_cfg=None, model_type="mixtral", window_sizes=None):
    protocol = getattr(args, "completion_protocol_data", None)
    build_started = time.perf_counter()
    use_amp = args.baseline_opts and not args.no_amp and device.type == "cuda"
    print(f"\n{'='*70}\n[POLICY = {policy}]\n{'='*70}")
    if args.smoke:
        model, caches, _cfg = MT.build_smoke_model(
            store, device, plan.placement, plan.k_h, plan.k_c, policy, args.cold_ssd,
            n_layers=smoke_cfg["n_layers"], n_experts=smoke_cfg["n_experts"],
            top_k=smoke_cfg["top_k"], hidden=smoke_cfg["hidden"],
            ffn=smoke_cfg["ffn"], vocab=smoke_cfg["vocab"])
    elif model_type == "deepseek":
        # DeepSeek 是对照场景 (CPU 装得下, 不落 SSD), 有意只用全局 k_h/k_c,
        # 不消费 compile_plan 产出的 per_layer_k_h/k_c —— 属预期行为, 非配置遗漏。
        model, caches = DT.build_tiered_model(
            args.state_path_resolved, args.state_path_resolved, store, device,
            plan.placement, plan.k_h, plan.k_c, policy=policy,
            cold_ssd=args.cold_ssd)
    else:
        # 仅当编译期确实产出了 per-layer 自适应分配 (per_layer_alpha 非空) 时才传 per-layer；
        # --uniform 时 per_layer_alpha 为空, 传 None 走全局 k_h/k_c, 避免误报 "per-layer adaptive"。
        model, caches = MT.build_tiered_model(
            args.state_path_resolved, args.state_path_resolved, store, device,
            plan.placement, plan.k_h, plan.k_c, policy=policy,
            cold_ssd=args.cold_ssd,
            per_layer_k_h=plan.per_layer_k_h if plan.per_layer_alpha else None,
            per_layer_k_c=plan.per_layer_k_c if plan.per_layer_alpha else None)

    initialization_s = time.perf_counter() - build_started
    request_rows = []
    if protocol:
        from completion_protocol import (RequestRecorder, append_request, digest,
                                         resident_state, storage_bytes)
        initial_residents = resident_state(caches)
        initial_storage = storage_bytes(caches)
        # The old batch fast path promotes before policy.access and labels those
        # CPU deliveries as HBM hits. Use policy-owned updates for every arm.
        for cache in caches:
            if cache is not None:
                cache._completion_sequential = True
        if not protocol.get("prefill_overlap", True):
            for cache in caches:
                if cache is not None:
                    cache.prefetch_ssd_batch = lambda *a, **kw: None
    # ── torch.compile 不适合动态 MoE (会触发达纳错误), 跳过 ──
    # cudnn.benchmark + TF32 在 main() 中已启用, 所有策略自动受益

    def memory_observer(run_phase, prompt_index, input_tokens):
        if not getattr(args, "trace_memory", False) or device.type != "cuda":
            return None

        def record(stage, step, elapsed_s):
            row = {"policy": policy, "run_phase": run_phase, "prompt_index": prompt_index,
                   "input_tokens": input_tokens, "stage": stage, "step": step,
                   "elapsed_ms": None if elapsed_s is None else round(elapsed_s * 1e3, 3),
                   "cuda_allocated_bytes": torch.cuda.memory_allocated(device),
                   "cuda_reserved_bytes": torch.cuda.memory_reserved(device),
                   "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(device),
                   **cache_memory_snapshot(caches)}
            print("MEMTRACE " + json.dumps(row, sort_keys=True), flush=True)

        return record

    # ---- 计时: 每个 prompt 跑一次, 取均值 ----
    def set_phase_all(phase):
        for c in caches:
            if c is not None:
                c.set_phase(phase)

    lat = []
    # Motivation III: 逐窗口命中/字节快照（任务切换序列 A→B/B→A/A→A 用）
    window_sizes = window_sizes or [len(prompts)]
    window_hits = []          # 每个窗口的 [hbm, cpu, ssd, cpu_compute] 增量
    window_ssd_bytes = []     # 每个窗口的 ssd_read 字节增量
    win_idx = 0
    win_count = 0
    win_snapshot = [0, 0, 0, 0]
    win_ssd_snapshot = 0
    for prompt_index, p in enumerate(prompts):
        if args.smoke:
            ids = torch.randint(0, smoke_cfg["vocab"], (1, args.prompt_len), device=device)
        else:
            ids = tokenizer(p, return_tensors="pt").input_ids[:, :args.prompt_len].to(device)
        input_tokens = ids.shape[1]
        # warmup 一次 (排除首次 kernel 编译/换页抖动)
        if not protocol or protocol["warmup"] == "per_request":
            set_phase_all("warmup")
            warmup_trace = memory_observer("warmup", prompt_index, input_tokens)
            if warmup_trace is not None:
                warmup_trace("before_forward", -1, None)
            _ = measure_latency(model, ids, min(4, args.max_new_tokens), device, use_cache,
                                use_amp=use_amp, trace_fn=warmup_trace)
        # measure 阶段：prefill 与 decode 分桶（X9 修复）
        measured_trace = memory_observer("measure", prompt_index, input_tokens)
        if measured_trace is not None:
            measured_trace("before_forward", -1, None)
        callback = set_phase_all
        recorder = None
        if protocol:
            block_dev = _store_device_name(args.store_root)
            recorder = RequestRecorder(caches, lambda: None if block_dev is None else _disk_sectors_read(block_dev), None)
            callback = recorder.boundary
        lat.append(measure_latency(model, ids, args.max_new_tokens, device, use_cache,
                                   use_amp=use_amp, trace_fn=measured_trace,
                                   phase_cb=callback))
        if recorder is not None:
            recorder.boundary("between_requests")
            row = {"request_index": prompt_index, "policy": policy,
                   "input": args.completion_input_rows[prompt_index],
                   "input_tokens": input_tokens, "input_token_sha256": digest(ids[0].tolist()),
                   "output_tokens": args.max_new_tokens, **lat[-1],
                   "phases": recorder.rows, "storage": storage_bytes(caches),
                   "residents_after": resident_state(caches)}
            row["input"] = {k: v for k, v in row["input"].items() if k != "text"}
            request_rows.append(row)
            append_request(os.path.join(os.path.dirname(os.path.abspath(args.out)), "requests.jsonl"), row)
        # 窗口边界：快照本窗口增量命中 + SSD 读字节
        win_count += 1
        if win_idx < len(window_sizes) and win_count >= window_sizes[win_idx]:
            cur = [0, 0, 0, 0]
            ssd_bytes = 0
            for c in caches:
                if c is None:
                    continue
                for i in range(4):
                    cur[i] += c.hits[i]
                ssd_bytes += c.io_bytes.get("ssd_read", 0)
            window_hits.append([cur[i] - win_snapshot[i] for i in range(4)])
            window_ssd_bytes.append(ssd_bytes - win_ssd_snapshot)
            win_snapshot = cur
            win_ssd_snapshot = ssd_bytes
            win_idx += 1
            win_count = 0

    agg = {
        "ttft_ms": round(statistics.mean(l["ttft_ms"] for l in lat), 2),
        "tpot_ms": round(statistics.mean(l["tpot_ms"] for l in lat), 2),
        # Keep enough precision for derived speedups.  Rounding 0.037 and 0.024
        # to 0.04 and 0.02 before division can manufacture an apparent 2.0x.
        "tokens_per_s": round(statistics.mean(l["tokens_per_s"] for l in lat), 6),
    }
    # ---- PPL (无损验证) ----
    for c in caches:
        if c is not None:
            c.set_phase("ppl")
    ppl = None if args.skip_ppl else measure_ppl(
        model, tokenizer, ppl_text, args.ppl_tokens, device, use_cache)
    agg["ppl"] = round(ppl, 3) if ppl is not None else "exact(lossless)"

    # ---- 命中率 (跨层汇总) ----
    tot = [0, 0, 0, 0]
    for c in caches:
        if c is None:
            continue
        for i in range(4):
            tot[i] += c.hits[i]
    s = sum(tot) or 1
    agg["hit_pct"] = {"hbm": round(tot[0]/s*100, 1), "cpu": round(tot[1]/s*100, 1),
                      "ssd": round(tot[2]/s*100, 1), "cpu_compute": round(tot[3]/s*100, 1)}
    # X9 分阶段命中 + 字节计量
    phase_hits = {}
    io_bytes = {"ssd_read": 0, "h2d": 0, "d2h": 0}
    for c in caches:
        if c is None:
            continue
        for ph, arr in c.phase_hits.items():
            acc = phase_hits.setdefault(ph, [0, 0, 0, 0])
            for i in range(4):
                acc[i] += arr[i]
        for k in io_bytes:
            io_bytes[k] += c.io_bytes[k]
    agg["phase_hits"] = phase_hits
    agg["io_bytes"] = io_bytes
    agg["window_hits"] = window_hits        # Motivation III: 逐窗口增量命中 [hbm,cpu,ssd,cpu_compute]
    agg["window_sizes"] = window_sizes      # 窗口边界（prompt 数）
    agg["window_ssd_bytes"] = window_ssd_bytes  # Motivation III: 逐窗口 ssd_read 字节增量
    if protocol:
        agg["initialization_s"] = initialization_s
        agg["initial_residents"] = initial_residents
        agg["initial_storage"] = initial_storage
        agg["requests"] = request_rows
        agg["quality_status"] = "not_measured" if args.skip_ppl else "ppl_measured"
        agg["completion_protocol_sha256"] = protocol["sha256"]
        if device.type == "cuda":
            agg["cuda_peak_allocated_bytes"] = torch.cuda.max_memory_allocated(device)
            agg["cuda_peak_reserved_bytes"] = torch.cuda.max_memory_reserved(device)

    print(f"  TTFT={agg['ttft_ms']}ms  TPOT={agg['tpot_ms']}ms  "
          f"throughput={agg['tokens_per_s']} tok/s  PPL={agg['ppl']}")
    print(f"  hit: HBM={agg['hit_pct']['hbm']}% CPU={agg['hit_pct']['cpu']}% "
          f"SSD={agg['hit_pct']['ssd']}% CPUcompute={agg['hit_pct']['cpu_compute']}%")

    del model, caches
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return agg


_STATUS_FILE = None

def _phase(name, **details):
    if not _STATUS_FILE:
        return
    value = {"phase": name, "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
             **details}
    atomic_write_result_status(_STATUS_FILE, value)

def atomic_write_result_status(path, value):
    target = os.path.abspath(path); parent = os.path.dirname(target) or "."
    os.makedirs(parent, exist_ok=True)
    import tempfile
    fd, temporary = tempfile.mkstemp(prefix=".status.", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)

def _emit_partial(args, device, plan, results, smoke):
    if not args.partial_out:
        return
    out = _build_result(args, device, plan, results, smoke)
    out["partial"] = True
    out["completed_policies"] = list(results)
    atomic_write_result(args.partial_out, out, results.keys())

def _main():
    global _STATUS_FILE
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mistralai/Mixtral-8x7B-Instruct-v0.1")
    ap.add_argument("--model_type", default="auto", choices=["auto", "mixtral", "deepseek"],
                    help="模型架构类型, auto 自动检测")
    ap.add_argument("--state_path", default=None, help="模型 snapshot 目录 (含 *.safetensors)。空则自动下载")
    ap.add_argument("--store_root", default="/tmp/mecc_store", help="SSD expert 冷存目录")
    ap.add_argument("--hbm_budget", type=float, default=22.0, help="留给 expert 的 HBM (GB)")
    ap.add_argument("--cpu_budget", type=float, default=40.0, help="留给 expert 的系统内存 (GB)")
    ap.add_argument("--alpha", type=float, default=1.0, help="profiled Zipf α (compile 用)")
    ap.add_argument("--profile", default=None, help="profile_real_moe.py 产出 (含 per_layer_counts 可选)")
    ap.add_argument("--baseline_opts", action="store_true", default=False,
                    help="启用 PyTorch 内置优化 (cudnn benchmark, TF32, AMP autocast). 所有策略自动受益")
    ap.add_argument("--no_amp", action="store_true", default=False,
                    help="在 baseline_opts 中禁用 AMP (仅保留 TF32+cudnn)")
    ap.add_argument("--policies", default="all", help="逗号分隔, 或 all")
    ap.add_argument("--prompt_len", type=int, default=64)
    ap.add_argument("--max_new_tokens", type=int, default=64)
    ap.add_argument("--n_prompts", type=int, default=8)
    ap.add_argument("--ppl_tokens", type=int, default=1024)
    ap.add_argument("--skip_ppl", action="store_true")
    ap.add_argument("--trace_memory", action="store_true",
                    help="诊断用：每个 prefill/decode 步把 CUDA 与专家缓冲占用写入日志")
    ap.add_argument("--cold_ssd", action="store_true", default=True, help="SSD 真冷读 (默认开)")
    ap.add_argument("--warm_ssd", dest="cold_ssd", action="store_false")
    ap.add_argument("--uniform", action="store_true", default=False,
                    help="统一 per-layer 分配 (不生成随机 per_layer_alpha, 与之前 A100 实验一致)")
    ap.add_argument("--init-plan", default="per_layer", choices=["per_layer", "global", "avg"],
                    help="Insight I: 初始放置策略 (per_layer=逐层热度 / global=全局热度 / avg=平均配额)")
    ap.add_argument("--update-rule", default=None, choices=["joint", "independent", "fixed_cpu"],
                    help="Insight II: 缓存更新规则; 指定后覆盖 --policies (joint=ours / independent / fixed_cpu=swapmoe)")
    ap.add_argument("--task-seq", default="none", choices=["none", "a_b", "b_a", "a_a"],
                    help="Motivation III: 任务切换序列 (none / A→B / B→A / A→A)")
    ap.add_argument("--platform", default=None,
                    help="真实实验平台名称；未指定时从当前 torch device 自动检测")
    ap.add_argument("--smoke", action="store_true", help="本机自检: 微型随机 MoE, 不下载")
    ap.add_argument("--out", default="main_table.json")
    ap.add_argument("--partial_out", default=None,
                    help="atomic Schema-A checkpoint updated after each completed policy")
    ap.add_argument("--status_file", default=None, help="atomic phase-status JSON for persistent runs")
    ap.add_argument("--input_manifest", default=None,
                    help="离线固定输入清单 JSON（QA/Code/PPL/画像 + token 哈希），优先于网络下载")
    ap.add_argument("--completion-protocol", default=None,
                    help="frozen offline request/measurement contract; legacy defaults unchanged")
    args = ap.parse_args()
    args.completion_protocol_data = None
    if args.completion_protocol:
        from completion_protocol import load_protocol
        args.completion_protocol_data, args.completion_bundle = load_protocol(args.completion_protocol)
        # The monitor lives in this run's unit and samples loading as well as inference.
        if os.path.isdir("/proc/self") and args.status_file:
            import subprocess, sys, atexit
            monitor = subprocess.Popen([
                sys.executable, os.path.join(os.path.dirname(__file__), "resource_monitor.py"),
                "--pid", str(os.getpid()), "--out",
                os.path.join(os.path.dirname(os.path.abspath(args.out)), "resource_trace.jsonl"),
                "--status-file", args.status_file, "--interval", "1"])
            def stop_monitor():
                if monitor.poll() is None:
                    monitor.terminate()
                    try:
                        monitor.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        monitor.kill()
            atexit.register(stop_monitor)
    _STATUS_FILE = args.status_file
    _phase("initializing")

    device = get_device()
    if args.completion_protocol_data and (device.type != "cuda" or "A100" not in torch.cuda.get_device_name(device)):
        raise RuntimeError("the frozen completion protocol requires the assigned A100, not CPU fallback")
    print("=" * 70)
    print("MECC End-to-End: REAL MoE Compile→Run (TTFT/TPOT/tokens·s / PPL)")
    print("=" * 70)
    print(f"Device: {device}")

    # ── 启用 PyTorch 内置优化 (所有策略自动受益, 零人工 bias) ──
    if args.baseline_opts and device.type == "cuda":
        torch.backends.cudnn.benchmark = True
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        amp_status = "" if args.no_amp else " + AMP autocast"
        print(f"[opts] cudnn.benchmark + TF32{amp_status}")
    else:
        print("[opts] baseline (no torch-level optimizations)")

    if getattr(args, 'update_rule', None):
        # Insight II: --update-rule 覆盖 --policies，映射到单一策略（冻结其他变量只换更新规则）
        policies = [UPDATE_RULE_TO_POLICY[args.update_rule]]
    else:
        policies = POLICIES if args.policies == "all" else args.policies.split(",")

    # ───────────── SMOKE: 本机微型自检 ─────────────
    if args.smoke:
        _phase("smoke")
        smoke_cfg = dict(n_layers=2, n_experts=8, top_k=2, hidden=128, ffn=256, vocab=512)
        # 保留 GPU 测试 (非 CPU)
        if device.type != "cuda":
            device = torch.device("cpu")
        store = SSDExpertStore(os.path.join(args.store_root, "smoke"),
                               smoke_cfg["hidden"], smoke_cfg["ffn"], dtype=torch.float32)
        MT.materialize_smoke_experts(store, device, smoke_cfg["n_layers"],
                                     smoke_cfg["n_experts"], smoke_cfg["hidden"], smoke_cfg["ffn"])
        plan = compile_plan("smoke", hbm_budget_gb=0.0006, cpu_budget_gb=0.0008,
                            alpha=args.alpha, n_layers=2, n_experts=8, expert_mb=0.2)
        plan.k_h, plan.k_c = 2, 3   # 固定小预算便于触发三级换页
        print_plan(plan)
        args.prompt_len = 8
        args.max_new_tokens = 6
        prompts = list(range(args.n_prompts))
        results = {}
        for policy in policies:
            _phase("running_policy", policy=policy, completed_policies=list(results),
                   partial_output=os.path.abspath(args.partial_out) if args.partial_out else None)
            results[policy] = run_policy(policy, args, plan, store, device, prompts, None, None,
                                         use_cache=False, smoke_cfg=smoke_cfg)
            _emit_partial(args, device, plan, results, smoke=True)
        _emit(args, device, plan, results, smoke=True)
        _phase("complete", output=os.path.abspath(args.out))
        return

    # ───────────── 真实模型 ─────────────
    from transformers import AutoTokenizer, AutoConfig
    args.state_path_resolved = resolve_state_path(args.model, args.state_path)
    _phase("loading_model_metadata", state_path=args.state_path_resolved)
    tokenizer = AutoTokenizer.from_pretrained(args.state_path_resolved, trust_remote_code=True)

    # 生成 per-layer α (模拟真实 profiling; 真实场景用 profile_deepseek.py 等的产出)
    # --uniform 跳过 per-layer adaptive, 使用统一分配 (与之前 A100 Mixtral 成功实验一致)
    import random; random.seed(42)
    cfg = AutoConfig.from_pretrained(args.state_path_resolved, trust_remote_code=True)
    n_layers = cfg.num_hidden_layers
    protocol = args.completion_protocol_data
    if protocol and protocol["allocation"] == "profile":
        from completion_protocol import measured_alpha
        if not args.profile or hashlib.sha256(open(args.profile, "rb").read()).hexdigest() != protocol.get("profile_sha256"):
            raise ValueError("missing or changed allocation profile")
        per_layer_alpha = measured_alpha(args.profile, n_layers)
    elif protocol or getattr(args, 'uniform', False):
        per_layer_alpha = None
        print("  [compile] uniform allocation (no per-layer alpha)")
    else:
        per_layer_alpha = [max(0.5, min(2.0, random.gauss(args.alpha, 0.3))) for _ in range(n_layers)]
    planning_hbm, planning_cpu = args.hbm_budget, args.cpu_budget
    if protocol and protocol.get("equal_uniform_slots"):
        _, ne, _, expert_mb = MODEL_SPECS[args.model]
        size = expert_mb / 1024
        kh = min(ne, int(args.hbm_budget / n_layers / size))
        kc = min(ne - kh, int(args.cpu_budget / n_layers / size))
        planning_hbm, planning_cpu = kh * n_layers * size, kc * n_layers * size
    if protocol and args.profile:
        if hashlib.sha256(open(args.profile, "rb").read()).hexdigest() != protocol.get("profile_sha256"):
            raise ValueError("profile hash changed")
    plan = compile_plan(args.model, planning_hbm, planning_cpu,
                        alpha=args.alpha, profile_path=args.profile,
                        per_layer_alpha=per_layer_alpha,
                        init_plan=args.init_plan,
                        enable_m3=not bool(protocol and protocol.get("disable_m3")))
    print_plan(plan)

    # 自动检测模型类型
    mtype = args.model_type
    if mtype == "auto":
        mtype = MODEL_TYPE.get(args.model, "mixtral")
    print(f"  [model_type] {mtype}")

    # expert 一次性物化到 SSD (4 策略共享同一 store)
    cfg = AutoConfig.from_pretrained(args.state_path_resolved, trust_remote_code=True)
    if mtype == "deepseek":
        e_hidden = cfg.hidden_size
        e_ffn = cfg.moe_intermediate_size
        n_experts_total = cfg.n_routed_experts
    else:
        e_hidden = cfg.hidden_size
        e_ffn = cfg.intermediate_size
        n_experts_total = cfg.num_local_experts
    store = SSDExpertStore(args.store_root, e_hidden, e_ffn)
    _phase("validating_store", store_root=os.path.abspath(args.store_root))
    manifest = expected_manifest(
        model=args.model, model_type=mtype, state_path=args.state_path_resolved,
        n_layers=plan.n_layers, n_experts=plan.n_experts,
        hidden=e_hidden, ffn=e_ffn, expert_bytes=store.total_bytes,
        dtype=str(store.dtype))
    store_complete = validate_store(args.store_root, manifest)
    print(f"\n[materialize] streaming {plan.n_layers*plan.n_experts} experts → {args.store_root}")
    if store_complete:
        print("  [store] manifest and all expert files verified, skip materialization.")
    else:
        _phase("materializing_store", store_root=os.path.abspath(args.store_root))
        write_pending_manifest(args.store_root, manifest)
        if mtype == "deepseek":
            DT.materialize_experts_to_ssd(args.state_path_resolved, store,
                                          plan.n_layers, plan.n_experts)
        else:
            MT.materialize_experts_to_ssd(args.state_path_resolved, store,
                                          plan.n_layers, plan.n_experts)
        write_manifest(args.store_root, manifest)
        print("  [store] manifest finalized after integrity check.")

    if protocol:
        from completion_protocol import select_inputs
        prompts, ppl_text, args.completion_input_rows = select_inputs(protocol, args.completion_bundle, args.n_prompts)
        window_sizes = [1] * len(prompts)
    else:
        input_manifest = load_manifest(args.input_manifest) if args.input_manifest else None
        prompts, ppl_text = load_prompts(
            args.n_prompts, args.prompt_len, use_wikitext=not args.skip_ppl,
            manifest=input_manifest)
        task_b_prompts = GSM8K_PROMPTS if args.task_seq in ("a_b", "b_a") else None
        prompts, window_sizes = organize_task_sequence(prompts, args.task_seq, task_b_prompts)
    prompt_digest = hashlib.sha256(json.dumps(prompts, ensure_ascii=False).encode()).hexdigest()
    ppl_digest = hashlib.sha256(ppl_text.encode()).hexdigest()
    ppl_input_tokens = tokenizer(ppl_text, return_tensors="pt").input_ids[:, :args.ppl_tokens].shape[1]
    print(f"  [inputs] prompts_sha256={prompt_digest} ppl_text_sha256={ppl_digest} "
          f"ppl_input_tokens={ppl_input_tokens}", flush=True)
    # 块设备物理读字节采样（口径核对：应用请求字节 ssd_read vs 块设备物理读 vs 进程 read）
    block_dev = _store_device_name(args.store_root)
    disk_start = _disk_sectors_read(block_dev)
    proc_start = _proc_read_bytes()
    results = {}
    for policy in policies:
        _phase("running_policy", policy=policy, completed_policies=list(results),
               partial_output=os.path.abspath(args.partial_out) if args.partial_out else None)
        results[policy] = run_policy(policy, args, plan, store, device, prompts, ppl_text,
                                     tokenizer, use_cache=True, model_type=mtype,
                                     window_sizes=window_sizes)
        _emit_partial(args, device, plan, results, smoke=False)
    block_io = {
        "device": block_dev,
        "disk_read_bytes": _disk_sectors_read(block_dev) - disk_start,
        "proc_read_bytes": _proc_read_bytes() - proc_start,
    }
    _emit(args, device, plan, results, smoke=False, block_io=block_io)
    _phase("complete", output=os.path.abspath(args.out), completed_policies=list(results))

def main():
    try:
        return _main()
    except BaseException as exc:
        _phase("failed", error_type=type(exc).__name__, error=str(exc))
        raise


def _compute_speedups(results):
    # speedup vs baselines (按 throughput)
    if "ours" in results:
        ours_tps = results["ours"]["tokens_per_s"]
        for b in ("swapmoe", "fiddler", "naive", "flashmoe_rf_adaptation"):
            if b in results and results[b]["tokens_per_s"] > 0:
                results["ours"].setdefault("speedup_vs", {})[b] = round(
                    ours_tps / results[b]["tokens_per_s"], 3)


def _detect_platform(args, device):
    if args.platform:
        return args.platform
    if device.type == "cuda":
        return torch.cuda.get_device_name(device)
    return "CPU"


def _profile_identity(profile_path):
    """返回画像文件身份：路径、sha256、是否含 per_layer_counts / per_layer_trace。

    对应 Insight I 前置：主 JSON 须保存画像身份，才能复现「逐层真实画像」初态。
    """
    if not profile_path:
        return None
    ident = {"path": profile_path, "has_per_layer_counts": False,
             "has_per_layer_trace": False, "sha256": None}
    try:
        with open(profile_path, "rb") as f:
            ident["sha256"] = hashlib.sha256(f.read()).hexdigest()
    except OSError:
        pass
    try:
        with open(profile_path, encoding="utf-8") as f:
            prof = json.load(f)
        ident["has_per_layer_counts"] = bool(prof.get("per_layer_counts"))
        ident["has_per_layer_trace"] = bool(prof.get("per_layer_trace"))
    except (OSError, ValueError):
        pass
    return ident


def _build_result(args, device, plan, results, smoke, block_io=None):
    _compute_speedups(results)
    out = {
        "device": str(device),
        "mode": "smoke" if smoke else "real",
        "model": args.model if not smoke else "smoke-tiny-moe",
        "platform": _detect_platform(args, device),
        "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "compiled_plan": {k: v for k, v in vars(plan).items() if k != "placement"},
        "config": {"max_new_tokens": args.max_new_tokens, "prompt_len": args.prompt_len,
                   "n_prompts": args.n_prompts, "cold_ssd": args.cold_ssd},
        "results": results,
    }
    prof_ident = _profile_identity(args.profile)
    if getattr(args, "completion_protocol_data", None):
        out["completion_protocol"] = args.completion_protocol_data
        out["compiled_plan"]["placement"] = plan.placement
        out["config"]["actual_requests"] = len(args.completion_input_rows)
    if prof_ident is not None:
        out["profile"] = prof_ident
    if block_io is not None:
        out["block_io"] = block_io
    return out


def _emit(args, device, plan, results, smoke, block_io=None):
    out = _build_result(args, device, plan, results, smoke, block_io)
    atomic_write_result(args.out, out, results.keys())
    print(f"\n{'='*70}\nMAIN TABLE → {args.out}")
    print(f"{'policy':<10}{'TTFT(ms)':>11}{'TPOT(ms)':>11}{'tok/s':>10}{'PPL':>16}")
    for p, r in results.items():
        print(f"{p:<10}{r['ttft_ms']:>11}{r['tpot_ms']:>11}{r['tokens_per_s']:>10}{str(r['ppl']):>16}")
    if "ours" in results and results["ours"].get("speedup_vs"):
        sv = results["ours"]["speedup_vs"]
        print("  OURS speedup: " + " | ".join(f"vs {k} {v}×" for k, v in sv.items()))
    print("=" * 70)


if __name__ == "__main__":
    main()
