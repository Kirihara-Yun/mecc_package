#!/usr/bin/env python3
"""
mecc_framework.models.mixtral — Mixtral 适配器
================================================
适配 mistralai/Mixtral-8x7B-Instruct-v0.1 (block_sparse_moe 结构)。
"""
from __future__ import annotations
import os
import json
from glob import glob
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn

from ..base.config import ModelSpec, ExpertSpec, OffloadConfig
from ..base.store import ExpertSSDStore
from ..cache.engine import LayerExpertCache
from ..layers.moe_forward import UniversalSparseMoe
from .base import ModelAdapter


class MixtralAdapter(ModelAdapter):
    """Mixtral MoE 模型适配器。

    Expert 命名: model.layers.{L}.block_sparse_moe.experts.{E}.w{1,2,3}.weight
    Gate 命名:   model.layers.{L}.block_sparse_moe.gate.weight
    """

    @property
    def model_spec(self) -> ModelSpec:
        if self._model_spec is None:
            self._model_spec = ModelSpec(
                name=self.model_id,
                n_layers=32,
                n_experts=8,
                top_k=2,
                expert_spec=ExpertSpec(
                    hidden_dim=4096,
                    ffn_dim=14336,
                    nbytes_fp16=2 * (4096 * 14336 + 14336 * 4096 + 4096 * 14336),
                ),
            )
        return self._model_spec

    def parse_expert_key(self, key: str) -> Optional[Tuple[int, int, str]]:
        """model.layers.{L}.block_sparse_moe.experts.{E}.w{n}.weight → (L, E, wn)"""
        if ".block_sparse_moe.experts." not in key:
            return None
        parts = key.split(".")
        try:
            L = int(parts[parts.index("layers") + 1])
            E = int(parts[parts.index("experts") + 1])
            wn = parts[-2]  # w1 / w2 / w3
            if wn not in ("w1", "w2", "w3"):
                return None
        except (ValueError, IndexError):
            return None
        return L, E, wn

    def is_gate_key(self, key: str) -> bool:
        return key.endswith(".block_sparse_moe.gate.weight")

    def is_expert_key(self, key: str) -> bool:
        return self.parse_expert_key(key) is not None

    def build_tiered_model(self,
                           state_path: str,
                           store: ExpertSSDStore,
                           device: torch.device,
                           config: OffloadConfig
                           ) -> Tuple[nn.Module, List[LayerExpertCache]]:
        from transformers import AutoConfig, AutoModelForCausalLM
        from accelerate import init_empty_weights
        from accelerate.utils import set_module_tensor_to_device
        from safetensors import safe_open

        spec = self.model_spec
        hf_config = AutoConfig.from_pretrained(self.model_id)
        hf_config.torch_dtype = torch.float16

        print(f"  [build] skeleton on meta device ({spec.n_layers} layers, "
              f"{spec.n_experts} experts/layer)...")
        with init_empty_weights():
            model = AutoModelForCausalLM.from_config(hf_config, torch_dtype=torch.float16)

        # 加载 trunk + gate; expert 跳过 (已在 SSD)
        shards = sorted(glob(os.path.join(state_path, "*.safetensors")))
        loaded = 0
        for shard in shards:
            with safe_open(shard, framework="pt", device="cpu") as f:
                for key in f.keys():
                    if self.is_expert_key(key):
                        continue
                    set_module_tensor_to_device(
                        model, key, device,
                        value=f.get_tensor(key).to(torch.float16))
                    loaded += 1
        print(f"  [build] loaded {loaded} trunk/gate tensors → {device}")
        model.eval()

        # 逐层替换 block_sparse_moe 为三级缓存版
        caches: List[LayerExpertCache] = []
        for L in range(spec.n_layers):
            layer = model.model.layers[L]
            moe = layer.block_sparse_moe
            gate = moe.gate

            ranked = [(L, e) for e in config.get_static_placement(L)]
            cache = LayerExpertCache(
                layer_id=L, store=store, budget=config.budget,
                device=device, config=config, ranked_uids=ranked,
            )
            layer.block_sparse_moe = UniversalSparseMoe(
                hidden_dim=spec.expert_spec.hidden_dim,
                ffn_dim=spec.expert_spec.ffn_dim,
                n_experts=spec.n_experts,
                top_k=spec.top_k,
                layer_id=L,
                gate=gate,
                cache=cache,
                gate_mode="softmax_topk",
            )
            caches.append(cache)

        if device.type == "cuda":
            torch.cuda.synchronize(device)
        print(f"  [build] {config.policy.value}: per-layer K_H={config.budget.k_hbm}"
              f" (GPU) + K_C={config.budget.k_cpu} (CPU)")
        return model, caches
