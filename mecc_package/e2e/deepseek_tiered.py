#!/usr/bin/env python3
"""
deepseek_tiered.py — 把 DeepSeek-V2-Lite MoE 模型接到三级缓存 (lossless)
==========================================================================
适配 DeepSeekMoE 架构的特殊之处:
  1) Layer 0 是 dense FFN (非 MoE), Layer 1..26 是 MoE
  2) 每层 64 routed + 2 shared experts, top-6 routing
  3) Gate (MoEGate) 已内置 top-k 选择, forward 返回 (topk_idx, topk_weight, aux_loss)
  4) Shared experts 始终激活, 常驻 GPU

与 mixtral_tiered.py 共享 tiered_engine.py 的核心 (ExpertWeights, SSDExpertStore, LayerExpertCache)。
"""
from __future__ import annotations
import json
import os
from glob import glob
from typing import Dict, Iterator, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from tiered_engine import ExpertUID, ExpertWeights, SSDExpertStore, LayerExpertCache


# ════════════════════════════════════════════════════════════════════
# DeepSeekTieredSparseMoe — DeepSeek MoE 的三级缓存版
#   Gate 已在 GPU, forward 返回 (topk_idx, topk_weight);
#   Shared experts 常驻 GPU, 每次前向都算。
# ════════════════════════════════════════════════════════════════════

class DeepSeekTieredSparseMoe(nn.Module):
    def __init__(self, config, layer_id: int, gate: nn.Module,
                 cache: LayerExpertCache, shared_expert: Optional[ExpertWeights] = None):
        super().__init__()
        self.hidden_dim = config.hidden_size
        self.num_experts = config.n_routed_experts
        self.top_k = config.num_experts_per_tok
        self.layer_id = layer_id
        self.gate = gate              # MoEGate, 已在 GPU
        self.experts = cache          # LayerExpertCache (三级)
        self.shared_expert = shared_expert

    def forward(self, hidden_states: torch.Tensor):
        identity = hidden_states
        batch_size, sequence_length, hidden_dim = hidden_states.shape

        # Gate 期望 3D 输入 (bsz, seq_len, hidden)
        topk_idx, topk_weight, _aux_loss = self.gate(hidden_states)
        # topk_idx    : (bsz*seq_len, top_k)
        # topk_weight : (bsz*seq_len, top_k)

        hidden_states = hidden_states.view(-1, hidden_dim)

        final_hidden_states = torch.zeros(
            (batch_size * sequence_length, hidden_dim),
            dtype=hidden_states.dtype, device=hidden_states.device)

        active = topk_idx.flatten().unique().tolist()

        # 两阶段: 1) 批量预取所有 CPU miss 到 GPU  2) 先算 GPU hit, 再算 prefetched CPU
        cpu_miss_uids = [(self.layer_id, e) for e in active
                         if e not in self.experts.gpu and e not in self.experts.static_cpu]
        # 注意: swapmoe 的 static_cpu 也是 CPU, 但它在 batch_prefetch 中会被搬上 GPU
        self.experts.batch_prefetch(cpu_miss_uids)

        # Phase 1: GPU hits (HBM 命中, 权重已在 GPU, 直接算)
        # Phase 2: CPU hits (已批量预取到 GPU, sync 后算)
        for (_lid, expert_idx), expert_layer in self.experts.load_experts(
                *((self.layer_id, e) for e in active), unordered=True):
            # 找到所有由 expert_idx 处理的 token
            expert_mask = (topk_idx == expert_idx)  # (total_tokens, top_k)
            token_indices, weight_indices = torch.where(expert_mask)

            if token_indices.shape[0] == 0:
                continue

            # 如果权重还在 CPU (prefetch 未命中或 fiddler), 用缓存中的 GPU 版本
            if expert_layer.w1.device.type == "cpu":
                gpu_ws = self.experts.consume_prefetched((self.layer_id, expert_idx))
                if gpu_ws is not None:
                    expert_layer = gpu_ws
                # sync 批量预取 (首次 CPU miss 时等待全部拷贝完成)
                if self.experts._pending_copy:
                    self.experts.sync_copy()

            cur = hidden_states[token_indices]
            exp_dev = expert_layer.w1.device
            if exp_dev != cur.device:
                out = expert_layer(cur.to(exp_dev)).to(hidden_states.device)
            else:
                out = expert_layer(cur)

            # 乘以 gate weight
            out = out * topk_weight[token_indices, weight_indices].unsqueeze(-1).to(out.dtype)
            final_hidden_states.index_add_(0, token_indices, out.to(hidden_states.dtype))

        # Shared experts (始终激活)
        if self.shared_expert is not None:
            final_hidden_states = final_hidden_states + self.shared_expert(identity.view(-1, hidden_dim))

        final_hidden_states = final_hidden_states.reshape(batch_size, sequence_length, hidden_dim)
        return final_hidden_states


# ════════════════════════════════════════════════════════════════════
# Expert 权重名解析 (DeepSeek 命名约定)
# ════════════════════════════════════════════════════════════════════

def _parse_expert_key(key: str) -> Optional[Tuple[int, int, str]]:
    """解析: model.layers.{L}.mlp.experts.{E}.{proj}.weight → (L, E, proj)"""
    if ".mlp.experts." not in key:
        return None
    parts = key.split(".")
    try:
        L = int(parts[2])           # model.layers.{L}
        E = int(parts[parts.index("experts") + 1])  # experts.{E}
        proj = parts[-2]            # gate_proj / up_proj / down_proj
    except (ValueError, IndexError):
        return None
    return L, E, proj


def _parse_shared_key(key: str) -> Optional[Tuple[int, str]]:
    """解析: model.layers.{L}.mlp.shared_experts.{proj}.weight → (L, proj)"""
    if ".mlp.shared_experts." not in key:
        return None
    parts = key.split(".")
    try:
        L = int(parts[2])
        proj = parts[-2]
    except (ValueError, IndexError):
        return None
    return L, proj


def _parse_dense_key(key: str) -> Optional[Tuple[int, str]]:
    """Layer 0: model.layers.0.mlp.{proj}.weight → (0, proj) (非 expert, 是 dense)"""
    if ".mlp.experts." in key or ".mlp.shared_experts." in key or ".mlp.gate." in key:
        return None
    if ".mlp." not in key:
        return None
    parts = key.split(".")
    try:
        L = int(parts[2])
        if parts[-2] not in ("gate_proj", "up_proj", "down_proj"):
            return None
        proj = parts[-2]
    except (ValueError, IndexError):
        return None
    return L, proj


def _is_gate_key(key: str) -> bool:
    return key.endswith(".mlp.gate.weight")


def _is_expert_key(key: str) -> bool:
    """是否为应卸载到 SSD 的 routed expert 权重 (不含 shared)。"""
    return _parse_expert_key(key) is not None


# ════════════════════════════════════════════════════════════════════
# 1. 流式把 expert 抽到 SSD store
# ════════════════════════════════════════════════════════════════════

def materialize_experts_to_ssd(state_path: str, store: SSDExpertStore,
                               num_layers: int, num_experts: int,
                               first_moe: int = None) -> None:
    """用 safetensors 逐张量读取, 把每个 routed expert 的 (gate_proj, up_proj, down_proj) 落到 SSD store。
    已存在则跳过 (幂等, 支持断点续跑)。

    Args:
        first_moe: 第一个 MoE 层在模型中的 layer id (DeepSeek 为 1, 因为 layer 0 是 dense)。
                   若不传, 自动从 safetensors index 推断。
    """
    from safetensors import safe_open

    # 推断实际的 MoE 层 ID 范围
    if first_moe is None:
        first_moe, _ = _find_moe_layers(state_path)
    actual_layers = list(range(first_moe, first_moe + num_layers))

    # 若全部已物化则直接返回
    if all(store.has((L, E)) for L in actual_layers for E in range(num_experts)):
        print(f"  [store] all {num_layers*num_experts} experts already materialized, skip.")
        return

    shards = sorted(glob(os.path.join(state_path, "*.safetensors")))
    if not shards:
        raise FileNotFoundError(f"No .safetensors in {state_path}.")

    pending: Dict[Tuple[int, int], Dict[str, torch.Tensor]] = {}
    done = 0
    target = num_layers * num_experts
    proj_map = {"gate_proj": "w1", "up_proj": "w3", "down_proj": "w2"}

    for shard in shards:
        with safe_open(shard, framework="pt", device="cpu") as f:
            for key in f.keys():
                pe = _parse_expert_key(key)
                if pe is None:
                    continue
                L, E, proj = pe
                if store.has((L, E)):
                    continue
                wn = proj_map.get(proj)
                if wn is None:
                    continue
                pending.setdefault((L, E), {})[wn] = f.get_tensor(key)
                d = pending[(L, E)]
                if {"w1", "w2", "w3"} <= set(d.keys()):
                    store.put((L, E), d["w1"], d["w3"], d["w2"])
                    pending.pop((L, E))
                    done += 1
                    if done % 64 == 0 or done == target:
                        print(f"  [store] materialized {done}/{target} experts → {store.root}")
    if pending:
        raise RuntimeError(f"{len(pending)} experts incomplete (missing proj): {list(pending)[:3]}...")


# ════════════════════════════════════════════════════════════════════
# 2. 建骨架 + 加载 trunk/gate 到 GPU + 挂三级缓存
# ════════════════════════════════════════════════════════════════════

def build_tiered_model(model_name: str,
                       state_path: str,
                       store: SSDExpertStore,
                       device: torch.device,
                       placement: Dict[int, List[int]],
                       k_h: int,
                       k_c: int,
                       policy: str = "ours",
                       cold_ssd: bool = True,
                       dtype: torch.dtype = torch.float16):
    """返回 (model, caches)。model 可直接 .generate()。"""
    from transformers import AutoConfig, AutoModelForCausalLM
    from safetensors import safe_open

    # Monkey-patch: DeepSeek attention 的 assert bug
    # 文件中 assert attention_mask is not None → 删掉这个 assert (后续 if 已处理 None)
    import importlib, sys
    # 直接修改本地文件并清除模块缓存
    patch_file = os.path.join(state_path, "modeling_deepseek.py")
    if os.path.exists(patch_file):
        with open(patch_file) as f:
            content = f.read()
        if "assert attention_mask is not None" in content:
            content = content.replace("assert attention_mask is not None\n", "")
            with open(patch_file, "w") as f:
                f.write(content)
            print("  [build] patched attention_mask assert in local modeling_deepseek.py")
    for mod_name in list(sys.modules.keys()):
        if 'modeling_deepseek' in mod_name:
            del sys.modules[mod_name]

    config = AutoConfig.from_pretrained(model_name, trust_remote_code=True, local_files_only=True)
    config.torch_dtype = dtype
    num_layers = config.num_hidden_layers         # 27
    num_experts = config.n_routed_experts         # 64
    n_shared = config.n_shared_experts            # 2

    # 查找 MoE 层的起始/结束 (layer 0 是 dense)
    first_moe, last_moe = _find_moe_layers(state_path)

    print(f"  [build] {num_layers} layers, MoE layers: {first_moe}..{last_moe}, "
          f"{num_experts} routed + {n_shared} shared experts")

    # 用 from_pretrained 正常加载 (解决 init_empty_weights + eager attention 兼容问题)
    print(f"  [build] loading full model (fp16, eager attn, ~30GB)...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True, torch_dtype=dtype, attn_implementation="eager",
        device_map=None, local_files_only=True).eval()

    # 收集 shared expert 权重 + 保存 gate 引用后卸载 expert 权重
    shared_w = {}
    saved_gates = {}  # L → gate module
    for L in range(first_moe, last_moe + 1):
        layer = model.model.layers[L]
        moe = layer.mlp
        # 保存 gate (仍在 CPU, 后续 .to(device))
        saved_gates[L] = moe.gate
        # 提取 shared expert 权重
        if hasattr(moe, 'shared_experts') and moe.shared_experts is not None:
            sh = moe.shared_experts
            shared_w[L] = {
                "gate_proj": sh.gate_proj.weight.data.clone(),
                "up_proj": sh.up_proj.weight.data.clone(),
                "down_proj": sh.down_proj.weight.data.clone(),
            }
        # 释放 MoE 模块 (expert 权重不再需要, 已在 SSD)
        layer.mlp = None
    del moe  # break reference
    torch.cuda.empty_cache()
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    print(f"  [build] unloaded routed experts, cuda mem free")
    torch.cuda.empty_cache()
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    print(f"  [build] unloaded routed experts, cuda mem free")

    # 构建 shared expert ExpertWeights
    shared_experts_dict = {}
    for L, w in shared_w.items():
        shared_experts_dict[L] = ExpertWeights(w["gate_proj"], w["up_proj"], w["down_proj"]).to(device)

    # ── 加载 trunk 权重到 GPU (trunk 已在模型上, 只需 .to(device)) ──
    model = model.to(device)
    # Gate 也移到 GPU
    for L in saved_gates:
        saved_gates[L] = saved_gates[L].to(device)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    print(f"  [build] trunk + gate → {device}")

    # ── 逐层替换 mlp 为三级缓存版 ──
    caches: List[LayerExpertCache] = [None] * num_layers
    for L in range(first_moe, last_moe + 1):
        layer = model.model.layers[L]
        gate = saved_gates[L]                    # 之前保存的 MoEGate
        # placement 键从 0 开始, 对应 first_moe..last_moe; 用 offset 映射
        placed = placement.get(L - first_moe, list(range(num_experts)))
        ranked = [(L, e) for e in placed]
        cache = LayerExpertCache(L, store, ranked, k_h, k_c, device,
                                 policy=policy, cold_ssd=cold_ssd)
        shared_ws = shared_experts_dict.get(L)
        layer.mlp = DeepSeekTieredSparseMoe(config, L, gate, cache, shared_ws)
        caches[L] = cache

    model.eval()
    if device.type == "cuda":
        torch.cuda.synchronize(device)

    # 统计有效 MoE 层数
    n_moe = sum(1 for c in caches if c is not None)
    print(f"  [build] {policy}: {n_moe} MoE layers, per-layer K_H={k_h} (GPU) + K_C={k_c} (CPU), "
          f"shared experts on GPU")
    return model, caches


def _find_moe_layers(state_path: str) -> Tuple[int, int]:
    """通过扫描 safetensors 索引, 找到第一层和最后一层 MoE 的 layer id。
    层 0 是 dense MLP (无 gate 和 experts), 层 1..26 是 MoE。"""
    idx_path = os.path.join(state_path, "model.safetensors.index.json")
    if os.path.exists(idx_path):
        with open(idx_path) as f:
            idx = json.load(f)
        moe_layers = set()
        for k in idx.get("weight_map", {}).keys():
            pe = _parse_expert_key(k)
            if pe is not None:
                moe_layers.add(pe[0])
        if moe_layers:
            return min(moe_layers), max(moe_layers)

    # Fallback: 尝试 safetensors 文件
    from safetensors import safe_open
    moe_layers = set()
    shards = sorted(glob(os.path.join(state_path, "*.safetensors")))
    for shard in shards:
        with safe_open(shard, framework="pt", device="cpu") as f:
            for key in f.keys():
                pe = _parse_expert_key(key)
                if pe is not None:
                    moe_layers.add(pe[0])
    if moe_layers:
        return min(moe_layers), max(moe_layers)
    return 0, 0
