#!/usr/bin/env python3
"""
mixtral_tiered.py — 把真实 HF MoE 模型接到三级缓存 (lossless, 可 generate)
==========================================================================
复用 dvmazur/mixtral-offloading 的两点工程模式:
  1) init_empty_weights() 建"无 expert 显存占用"的骨架 → trunk/attn/gate 常驻 GPU。
  2) SparseMoeWrapper.forward(hidden_states) 的 expert dispatch 逻辑 (照搬, 见下)。
本文件的活: 用 safetensors **流式** 把每个 expert 抽到 SSDExpertStore (绝不整模型入内存),
然后把每层 block_sparse_moe 换成绑定到 LayerExpertCache 的 TieredSparseMoe。

支持:
  - mixtral : mistralai/Mixtral-8x7B-Instruct-v0.1 (主对标, fp16 ~90GB → 必须三级)
  - 任何 block_sparse_moe={gate, experts[i].(w1,w2,w3)} 结构的 HF MoE
  - --smoke : 不下载, 造一个微型随机 MoE, 在 CPU 上验证整条 pipeline
"""
from __future__ import annotations
import json
import os
from glob import glob
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from tiered_engine import ExpertUID, ExpertWeights, SSDExpertStore, LayerExpertCache


# ════════════════════════════════════════════════════════════════════
# TieredSparseMoe —— 复用 mixtral-offloading 的 forward, 接到三级缓存
#   关键改造: expert 可能在 GPU(ours/swapmoe/naive) 或 CPU(fiddler) 上,
#   forward 按 expert 权重所在 device 决定算在哪, 再把输出搬回 hidden 所在 device。
# ════════════════════════════════════════════════════════════════════

class TieredSparseMoe(nn.Module):
    def __init__(self, config, layer_id: int, gate: nn.Module, cache: LayerExpertCache):
        super().__init__()
        self.hidden_dim = config.hidden_size
        self.num_experts = config.num_local_experts
        self.top_k = config.num_experts_per_tok
        self.layer_id = layer_id
        self.gate = gate          # 常驻 GPU 的 router
        self.experts = cache      # LayerExpertCache (三级)

    def forward(self, hidden_states: torch.Tensor):
        batch_size, sequence_length, hidden_dim = hidden_states.shape
        hidden_states = hidden_states.view(-1, hidden_dim)
        router_logits = self.gate(hidden_states)

        full_weights = F.softmax(router_logits, dim=1, dtype=torch.float)
        routing_weights, selected_experts = torch.topk(full_weights, self.top_k, dim=-1)
        routing_weights /= routing_weights.sum(dim=-1, keepdim=True)
        routing_weights = routing_weights.to(hidden_states.dtype)

        # ── Router-logit 预测预取: 取 top-(k+1) 和 top-(k+2) 作为 near-miss ──
        _, near_miss_experts = torch.topk(full_weights, min(self.top_k + 2, self.num_experts), dim=-1)
        near_miss = set(near_miss_experts.flatten().tolist())
        near_miss.difference_update(selected_experts.flatten().tolist())  # 去除已选中的
        if near_miss:
            self.experts.prefetch_near_miss([(self.layer_id, e) for e in near_miss])

        final_hidden_states = torch.zeros(
            (batch_size * sequence_length, hidden_dim),
            dtype=hidden_states.dtype, device=hidden_states.device)

        expert_mask = torch.nn.functional.one_hot(
            selected_experts, num_classes=self.num_experts).permute(2, 1, 0)
        active = selected_experts.flatten().unique().tolist()

        # prefill 阶段并行 SSD 预取 (ours_io 策略使用)
        if sequence_length > 1:
            self.experts.prefetch_ssd_batch(
                [(self.layer_id, e) for e in active], is_prefill=True)

        for (_lid, expert_idx), expert_layer in self.experts.load_experts(
                *((self.layer_id, e) for e in active), unordered=True):
            idx, top_x = torch.where(expert_mask[expert_idx])
            if top_x.shape[0] == 0:
                continue
            top_x_list = top_x.tolist()
            idx_list = idx.tolist()
            current_state = hidden_states[None, top_x_list].reshape(-1, hidden_dim)

            # —— 按 expert 权重所在 device 计算 (fiddler: CPU; 其余: GPU) ——
            exp_dev = expert_layer.w1.device
            if exp_dev != current_state.device:
                cur = current_state.to(exp_dev)
                out = expert_layer(cur).to(hidden_states.device)
            else:
                out = expert_layer(current_state)
            out = out * routing_weights[top_x_list, idx_list, None]
            final_hidden_states.index_add_(0, top_x, out.to(hidden_states.dtype))

        final_hidden_states = final_hidden_states.reshape(batch_size, sequence_length, hidden_dim)
        return final_hidden_states, router_logits


# ════════════════════════════════════════════════════════════════════
# Expert 权重名解析 (Mixtral 命名约定)
# ════════════════════════════════════════════════════════════════════

def _parse_expert_key(key: str) -> Optional[Tuple[int, int, str]]:
    # model.layers.{L}.block_sparse_moe.experts.{E}.w{n}.weight
    if ".block_sparse_moe.experts." not in key:
        return None
    parts = key.split(".")
    try:
        L = int(parts[parts.index("layers") + 1])
        E = int(parts[parts.index("experts") + 1])
        wname = parts[-2]   # w1 / w2 / w3
    except (ValueError, IndexError):
        return None
    return L, E, wname


def _is_gate_key(key: str) -> bool:
    return key.endswith(".block_sparse_moe.gate.weight")


# ════════════════════════════════════════════════════════════════════
# 1. 流式把 expert 抽到 SSD store (绝不整模型入内存)
# ════════════════════════════════════════════════════════════════════

def materialize_experts_to_ssd(state_path: str, store: SSDExpertStore,
                               num_layers: int, num_experts: int) -> None:
    """用 safetensors 逐张量读取, 把每个 expert 的 (w1,w3,w2) 落到 SSD store。
    已存在则跳过 (幂等, 支持断点续跑)。"""
    from safetensors import safe_open

    # 若全部已物化则直接返回
    if all(store.has((L, E)) for L in range(num_layers) for E in range(num_experts)):
        print(f"  [store] all {num_layers*num_experts} experts already materialized, skip.")
        return

    shards = sorted(glob(os.path.join(state_path, "*.safetensors")))
    if not shards:
        raise FileNotFoundError(f"No .safetensors in {state_path}. 先 snapshot_download 模型。")

    pending: Dict[Tuple[int, int], Dict[str, torch.Tensor]] = {}
    done = 0
    target = num_layers * num_experts
    for shard in shards:
        with safe_open(shard, framework="pt", device="cpu") as f:
            for key in f.keys():
                pe = _parse_expert_key(key)
                if pe is None:
                    continue
                L, E, wname = pe
                if store.has((L, E)):
                    continue
                pending.setdefault((L, E), {})[wname] = f.get_tensor(key)
                d = pending[(L, E)]
                if {"w1", "w2", "w3"} <= set(d.keys()):
                    store.put((L, E), d["w1"], d["w3"], d["w2"])
                    pending.pop((L, E))
                    done += 1
                    if done % 32 == 0 or done == target:
                        print(f"  [store] materialized {done}/{target} experts → {store.root}")
    if pending:
        raise RuntimeError(f"{len(pending)} experts incomplete (missing w*): {list(pending)[:3]}...")


# ════════════════════════════════════════════════════════════════════
# 2. 建骨架 + 加载 trunk/gate 到 GPU + 挂三级缓存
# ════════════════════════════════════════════════════════════════════

def build_tiered_model(model_name: str,
                       state_path: str,
                       store: SSDExpertStore,
                       device: torch.device,
                       placement: Dict[int, List[int]],   # layer → 按热度降序的 expert id
                       k_h: int,
                       k_c: int,
                       policy: str = "ours",
                       cold_ssd: bool = True,
                       dtype: torch.dtype = torch.float16,
                       per_layer_k_h: Optional[List[int]] = None,
                       per_layer_k_c: Optional[List[int]] = None):
    """返回 (model, caches)。model 可直接 .generate()。"""
    from transformers import AutoConfig, AutoModelForCausalLM
    from accelerate import init_empty_weights
    from accelerate.utils import set_module_tensor_to_device
    from safetensors import safe_open

    config = AutoConfig.from_pretrained(model_name)
    config.torch_dtype = dtype
    num_layers = config.num_hidden_layers
    num_experts = config.num_local_experts

    print(f"  [build] skeleton on meta device ({num_layers} layers, {num_experts} experts/layer)...")
    with init_empty_weights():
        model = AutoModelForCausalLM.from_config(config, torch_dtype=dtype)

    # ── 加载 trunk + gate (非 expert 权重) 到 GPU; expert 权重跳过 (已在 SSD) ──
    shards = sorted(glob(os.path.join(state_path, "*.safetensors")))
    loaded = 0
    for shard in shards:
        with safe_open(shard, framework="pt", device="cpu") as f:
            for key in f.keys():
                if _parse_expert_key(key) is not None:
                    continue   # expert → 已在 SSD, 不进模型
                set_module_tensor_to_device(model, key, device, value=f.get_tensor(key).to(dtype))
                loaded += 1
    print(f"  [build] loaded {loaded} trunk/gate tensors → {device}")
    model.eval()

    # ── 逐层替换 block_sparse_moe 为三级缓存版 (支持 per-layer 自适应分配) ──
    caches: List[LayerExpertCache] = []
    has_per_layer = per_layer_k_h is not None and len(per_layer_k_h) == num_layers
    for L in range(num_layers):
        layer = model.model.layers[L]
        moe = layer.block_sparse_moe
        gate = moe.gate                                  # 已在 GPU (trunk 阶段加载)
        ranked = [(L, e) for e in placement.get(L, list(range(num_experts)))]
        l_kh = per_layer_k_h[L] if has_per_layer else k_h
        l_kc = per_layer_k_c[L] if has_per_layer and per_layer_k_c else k_c
        cache = LayerExpertCache(L, store, ranked, l_kh, l_kc, device,
                                 policy=policy, cold_ssd=cold_ssd)
        layer.block_sparse_moe = TieredSparseMoe(config, L, gate, cache)
        caches.append(cache)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    if has_per_layer:
        kh_dist = f"K_H∈[{min(per_layer_k_h)}..{max(per_layer_k_h)}]"
        kc_dist = f"K_C∈[{min(per_layer_k_c)}..{max(per_layer_k_c)}]" if per_layer_k_c else ""
        print(f"  [build] {policy}: per-layer adaptive {kh_dist} {kc_dist}, total HBM={sum(per_layer_k_h)} slots")
    else:
        print(f"  [build] {policy}: per-layer K_H={k_h} (GPU) + K_C={k_c} (CPU), rest SSD")
    return model, caches


# ════════════════════════════════════════════════════════════════════
# 3. SMOKE: 微型随机 MoE, 不下载, CPU 上验证整条 pipeline
# ════════════════════════════════════════════════════════════════════

def build_smoke_model(store: SSDExpertStore, device: torch.device,
                      placement, k_h, k_c, policy, cold_ssd,
                      n_layers=2, n_experts=8, top_k=2, hidden=128, ffn=256, vocab=512):
    """造一个能跑 forward 的微型 MoE (非 HF), 用于本机自检三级缓存 + harness 逻辑。"""
    from types import SimpleNamespace

    class TinyAttn(nn.Module):
        def __init__(self, h):
            super().__init__()
            self.qkv = nn.Linear(h, h, bias=False)
        def forward(self, x):
            return x + self.qkv(x)

    class TinyLayer(nn.Module):
        def __init__(self, L, config):
            super().__init__()
            self.attn = TinyAttn(config.hidden_size)
            gate = nn.Linear(config.hidden_size, config.num_local_experts, bias=False).to(device)
            ranked = [(L, e) for e in placement.get(L, list(range(config.num_local_experts)))]
            cache = LayerExpertCache(L, store, ranked, k_h, k_c, device, policy=policy, cold_ssd=cold_ssd)
            self.block_sparse_moe = TieredSparseMoe(config, L, gate, cache)
            self.caches = cache
        def forward(self, x):
            x = self.attn(x)
            h, _ = self.block_sparse_moe(x)
            return x + h

    class TinyMoE(nn.Module):
        def __init__(self, config):
            super().__init__()
            self.embed = nn.Embedding(config.vocab_size, config.hidden_size).to(device)
            self.layers = nn.ModuleList([TinyLayer(L, config) for L in range(config.num_hidden_layers)])
            self.norm = nn.LayerNorm(config.hidden_size).to(device)
            self.lm_head = nn.Linear(config.hidden_size, config.vocab_size, bias=False).to(device)
        def forward(self, input_ids):
            x = self.embed(input_ids)
            for lyr in self.layers:
                x = lyr(x)
            return self.lm_head(self.norm(x))

    config = SimpleNamespace(hidden_size=hidden, intermediate_size=ffn,
                             num_local_experts=n_experts, num_experts_per_tok=top_k,
                             num_hidden_layers=n_layers, vocab_size=vocab)
    model = TinyMoE(config).to(device).eval()
    caches = [lyr.caches for lyr in model.layers]
    return model, caches, config


def materialize_smoke_experts(store: SSDExpertStore, device, n_layers, n_experts, hidden, ffn):
    """给 smoke 模型在 SSD 造随机 expert 权重 (与 store.shapes 一致: w1,w3 [ffn,hidden]; w2 [hidden,ffn])。"""
    g = torch.Generator().manual_seed(0)
    for L in range(n_layers):
        for E in range(n_experts):
            if store.has((L, E)):
                continue
            w1 = torch.randn(ffn, hidden, generator=g, dtype=torch.float32) * 0.02
            w3 = torch.randn(ffn, hidden, generator=g, dtype=torch.float32) * 0.02
            w2 = torch.randn(hidden, ffn, generator=g, dtype=torch.float32) * 0.02
            store.put((L, E), w1, w3, w2)
