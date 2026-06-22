#!/usr/bin/env python3
"""
mecc_framework.models.deepseek — DeepSeek 适配器
==================================================
适配 deepseek-ai/DeepSeek-V2-Lite (DeepSeekMoE 架构)。
特点: layer 0 dense, layer 1..26 MoE, shared experts, top-6 routing。
"""
from __future__ import annotations
import os
import json
import importlib
import sys
from glob import glob
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn

from ..base.config import ModelSpec, ExpertSpec, OffloadConfig
from ..base.expert import ExpertWeights
from ..base.store import ExpertSSDStore
from ..cache.engine import LayerExpertCache
from ..layers.moe_forward import UniversalSparseMoe
from .base import ModelAdapter


class DeepSeekAdapter(ModelAdapter):
    """DeepSeekMoE 模型适配器。

    Expert 命名:  model.layers.{L}.mlp.experts.{E}.{proj}.weight
    Shared 命名:  model.layers.{L}.mlp.shared_experts.{proj}.weight
    Gate 命名:    model.layers.{L}.mlp.gate.weight
    Layer 0:      model.layers.0.mlp.{proj}.weight (dense, 不卸载)
    """

    @property
    def model_spec(self) -> ModelSpec:
        if self._model_spec is None:
            self._model_spec = ModelSpec(
                name=self.model_id,
                n_layers=26,       # 27 层中 26 层 MoE (layer 0 是 dense)
                n_experts=64,      # routed experts (不含 2 shared)
                top_k=6,
                first_moe_layer=1,
                expert_spec=ExpertSpec(
                    hidden_dim=576,
                    ffn_dim=2048,
                    nbytes_fp16=2 * (576 * 2048 + 2048 * 576 + 576 * 2048),
                ),
            )
        return self._model_spec

    def parse_expert_key(self, key: str) -> Optional[Tuple[int, int, str]]:
        """model.layers.{L}.mlp.experts.{E}.{proj}.weight → (L, E, proj)"""
        if ".mlp.experts." not in key:
            # shared expert 不在这里解析
            return None
        parts = key.split(".")
        try:
            L = int(parts[2])
            E = int(parts[parts.index("experts") + 1])
            proj = parts[-2]
            proj_map = {"gate_proj": "w1", "up_proj": "w3", "down_proj": "w2"}
            wn = proj_map.get(proj)
            if wn is None:
                return None
        except (ValueError, IndexError):
            return None
        return L, E, wn

    def is_gate_key(self, key: str) -> bool:
        return key.endswith(".mlp.gate.weight")

    def is_expert_key(self, key: str) -> bool:
        return self.parse_expert_key(key) is not None

    def is_shared_key(self, key: str) -> bool:
        return ".mlp.shared_experts." in key

    def _patch_attention_assert(self, state_path: str):
        """修复 DeepSeek attention 的 assert bug (移除无效的 attention_mask assert)。"""
        patch_file = os.path.join(state_path, "modeling_deepseek.py")
        if not os.path.exists(patch_file):
            return
        with open(patch_file) as f:
            content = f.read()
        if "assert attention_mask is not None" in content:
            content = content.replace("assert attention_mask is not None\n", "")
            with open(patch_file, "w") as f:
                f.write(content)
            print("  [build] patched attention_mask assert")
        for mod_name in list(sys.modules.keys()):
            if "modeling_deepseek" in mod_name:
                del sys.modules[mod_name]

    def build_tiered_model(self,
                           state_path: str,
                           store: ExpertSSDStore,
                           device: torch.device,
                           config: OffloadConfig
                           ) -> Tuple[nn.Module, List[LayerExpertCache]]:
        from transformers import AutoConfig, AutoModelForCausalLM

        self._patch_attention_assert(state_path)

        spec = self.model_spec
        hf_config = AutoConfig.from_pretrained(self.model_id,
                                               trust_remote_code=True,
                                               local_files_only=True)
        hf_config.torch_dtype = torch.float16
        total_layers = hf_config.num_hidden_layers  # 27
        n_shared = hf_config.n_shared_experts       # 2

        first_moe, last_moe = 1, total_layers - 1   # layer 0 dense
        print(f"  [build] {total_layers} layers, MoE: {first_moe}..{last_moe}, "
              f"{spec.n_experts} routed + {n_shared} shared")

        # 全量加载模型
        print(f"  [build] loading full model fp16...")
        model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            trust_remote_code=True, torch_dtype=torch.float16,
            attn_implementation="eager",
            device_map=None, local_files_only=True).eval()

        # 提取 shared expert 权重 + gate, 然后释放 expert 权重
        shared_experts = {}
        saved_gates = {}
        for L in range(first_moe, last_moe + 1):
            layer = model.model.layers[L]
            moe = layer.mlp
            saved_gates[L] = moe.gate
            if hasattr(moe, "shared_experts") and moe.shared_experts is not None:
                sh = moe.shared_experts
                shared_experts[L] = ExpertWeights(
                    sh.gate_proj.weight.data.clone(),
                    sh.up_proj.weight.data.clone(),
                    sh.down_proj.weight.data.clone(),
                ).to(device)
            layer.mlp = None  # 释放 expert 权重

        torch.cuda.empty_cache()
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        print(f"  [build] unloaded routed experts, GPU memory freed")

        # trunk + gate → GPU
        model = model.to(device)
        for L in saved_gates:
            saved_gates[L] = saved_gates[L].to(device)
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        print(f"  [build] trunk + gate → {device}")

        # 逐层替换 mlp
        caches: List[Optional[LayerExpertCache]] = [None] * total_layers
        for L in range(first_moe, last_moe + 1):
            layer = model.model.layers[L]
            gate = saved_gates[L]
            ranked = [(L, e) for e in config.get_static_placement(L - first_moe)]
            cache = LayerExpertCache(
                layer_id=L, store=store, budget=config.budget,
                device=device, config=config, ranked_uids=ranked,
            )
            shared_ws = shared_experts.get(L)
            layer.mlp = UniversalSparseMoe(
                hidden_dim=spec.expert_spec.hidden_dim,
                ffn_dim=spec.expert_spec.ffn_dim,
                n_experts=spec.n_experts,
                top_k=spec.top_k,
                layer_id=L,
                gate=gate,
                cache=cache,
                gate_mode="sigmoid",
                shared_expert=shared_ws,
            )
            caches[L] = cache

        model.eval()
        if device.type == "cuda":
            torch.cuda.synchronize(device)

        n_moe = sum(1 for c in caches if c is not None)
        print(f"  [build] {config.policy.value}: {n_moe} MoE layers, "
              f"K_H={config.budget.k_hbm} + K_C={config.budget.k_cpu}, shared on GPU")
        return model, caches
