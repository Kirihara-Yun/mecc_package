#!/usr/bin/env python3
"""
mecc_framework.layers.moe_forward — 通用 MoE Forward (架构无关)
================================================================
核心来自 mixtral-offloading 的 SparseMoeWrapper.forward (expert dispatch 逻辑),
改造为架构无关版本:
  - 不依赖 MixtralConfig, 只依赖 (hidden_dim, ffn_dim, n_experts, top_k)
  - 支持多种 gate 输出格式 (softmax topk / sigmoid gate / DeepSeek MoEGate)
  - 按 expert 权重所在 device 决定计算位置 (GPU / CPU — fiddler 模式)
"""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple

from ..cache.engine import LayerExpertCache, ExpertUID


class UniversalSparseMoe(nn.Module):
    """架构无关的 Sparse MoE 前向层。

    支持 gate 三种模式:
      - "softmax_topk" : Mixtral 风格, softmax + top-k
      - "sigmoid"      : DeepSeek 风格, sigmoid gate (MoEGate 已内置 top-k)
      - "pre_routed"   : 外部已选好 expert, 直接传 topk_idx / topk_weight
    """

    def __init__(self,
                 hidden_dim: int,
                 ffn_dim: int,
                 n_experts: int,
                 top_k: int,
                 layer_id: int,
                 gate: nn.Module,
                 cache: LayerExpertCache,
                 gate_mode: str = "softmax_topk",
                 shared_expert: Optional[nn.Module] = None):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.ffn_dim = ffn_dim
        self.n_experts = n_experts
        self.top_k = top_k
        self.layer_id = layer_id
        self.gate = gate
        self.experts = cache
        self.gate_mode = gate_mode
        self.shared_expert = shared_expert

    def forward(self, hidden_states: torch.Tensor
                ) -> torch.Tensor:
        """主前向: dispatch tokens → experts → 加权聚合。"""
        identity = hidden_states
        batch_size, seq_len, hidden_dim = hidden_states.shape

        # ---- Gate routing ----
        if self.gate_mode == "sigmoid":
            # DeepSeek MoEGate: 返回 (topk_idx, topk_weight, aux_loss)
            topk_idx, topk_weight, _ = self.gate(hidden_states)
        elif self.gate_mode == "pre_routed":
            topk_idx, topk_weight = hidden_states  # 特殊: 整个传进来
            hidden_states = identity
        else:
            # softmax_topk: Mixtral 风格
            flat_hidden = hidden_states.view(-1, hidden_dim)
            router_logits = self.gate(flat_hidden)
            routing_weights = F.softmax(router_logits, dim=1, dtype=torch.float)
            routing_weights, selected_experts = torch.topk(routing_weights,
                                                           self.top_k, dim=-1)
            routing_weights /= routing_weights.sum(dim=-1, keepdim=True)
            routing_weights = routing_weights.to(flat_hidden.dtype)
            topk_idx = selected_experts
            topk_weight = routing_weights

        hidden_states = hidden_states.view(-1, hidden_dim)

        final_hidden = torch.zeros(
            (batch_size * seq_len, hidden_dim),
            dtype=hidden_states.dtype, device=hidden_states.device)

        # ---- Expert dispatch ----
        active_experts = topk_idx.flatten().unique().tolist()

        # 批量预取 CPU expert → GPU
        if torch.cuda.is_available():
            cpu_uids = {}
            for e in active_experts:
                uid = (self.layer_id, e)
                if uid not in self.experts.hbm:
                    ws = self.experts.cpu.get(uid) or self.experts.static_cpu.get(uid)
                    if ws is not None:
                        cpu_uids[uid] = ws
            if cpu_uids:
                self.experts._swap.batch_prefetch(cpu_uids)

        for (_lid, expert_idx), expert_layer in self.experts.load_experts(
                *((self.layer_id, e) for e in active_experts), unordered=True):

            expert_mask = (topk_idx == expert_idx)
            token_indices, weight_indices = torch.where(expert_mask)

            if token_indices.shape[0] == 0:
                continue

            # 如果权重还在 CPU (fiddler 预取未命中), 用预取缓冲中的 GPU 版本
            if expert_layer.device.type == "cpu":
                gpu_ws = self.experts._swap.consume_prefetched(
                    (self.layer_id, expert_idx))
                if gpu_ws is not None:
                    expert_layer = gpu_ws

            cur = hidden_states[token_indices]
            # 按 expert 权重所在 device 计算
            if expert_layer.device != cur.device:
                out = expert_layer(cur.to(expert_layer.device)).to(hidden_states.device)
            else:
                out = expert_layer(cur)

            out = out * topk_weight[token_indices, weight_indices].unsqueeze(-1).to(out.dtype)
            final_hidden.index_add_(0, token_indices, out.to(hidden_states.dtype))

        # shared expert (DeepSeek 架构)
        if self.shared_expert is not None:
            final_hidden = final_hidden + self.shared_expert(identity.view(-1, hidden_dim))

        final_hidden = final_hidden.reshape(batch_size, seq_len, hidden_dim)
        return final_hidden
