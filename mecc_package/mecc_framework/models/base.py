#!/usr/bin/env python3
"""
mecc_framework.models.base — 模型适配器抽象基类
=================================================
每个模型架构实现这个接口, 即可接入三级缓存框架。
"""
from __future__ import annotations
import os
import json
from abc import ABC, abstractmethod
from glob import glob
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn

from ..base.config import ModelSpec, ExpertSpec, OffloadConfig, CacheBudget
from ..base.store import ExpertSSDStore
from ..cache.engine import LayerExpertCache

ExpertUID = Tuple[int, int]


class ModelAdapter(ABC):
    """MoE 模型适配器抽象类。

    实现只需提供:
      - model_spec: 模型结构参数
      - parse_expert_key: 从 safetensors key 解析 (layer, expert, weight_name)
      - materialize_experts: 从 safetensors 流式抽 expert 到 SSD store
      - build_tiered_model: 加载模型 + 替换 MoE 层为三级缓存
    """

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._model_spec: Optional[ModelSpec] = None

    @property
    @abstractmethod
    def model_spec(self) -> ModelSpec:
        """返回模型规格。"""
        ...

    @abstractmethod
    def parse_expert_key(self, key: str) -> Optional[Tuple[int, int, str]]:
        """解析 safetensors key → (layer_id, expert_idx, weight_name)。

        weight_name: w1 / w2 / w3 / gate / shared / unknown
        """
        ...

    @abstractmethod
    def is_gate_key(self, key: str) -> bool:
        """判断是否为 router/gate 权重 key。"""
        ...

    @abstractmethod
    def is_expert_key(self, key: str) -> bool:
        """判断是否为应卸载到 SSD 的 expert 权重 key。"""
        ...

    # ----------------------------------------------------------------
    # 通用实现: streaming expert → SSD
    # ----------------------------------------------------------------

    def materialize_experts(self, state_path: str, store: ExpertSSDStore,
                            skip_existing: bool = True) -> None:
        """流式从 safetensors 提取所有 expert 到 SSD store。

        默认实现适用于大多数 block_sparse_moe 结构的 HF MoE。
        特殊架构 (如 DeepSeek 的 shared expert) 需要重写。
        """
        from safetensors import safe_open

        spec = self.model_spec
        n_layers = spec.n_layers
        n_experts = spec.n_experts

        if skip_existing and all(
                store.has((L, E)) for L in range(spec.first_moe_layer,
                                                  spec.first_moe_layer + n_layers)
                for E in range(n_experts)):
            print(f"  [store] all {n_layers * n_experts} experts already materialized, skip.")
            return

        shards = sorted(glob(os.path.join(state_path, "*.safetensors")))
        if not shards:
            raise FileNotFoundError(f"No .safetensors in {state_path}.")

        pending: Dict[Tuple[int, int], Dict[str, torch.Tensor]] = {}
        done = 0
        target = n_layers * n_experts

        for shard in shards:
            with safe_open(shard, framework="pt", device="cpu") as f:
                for key in f.keys():
                    parsed = self.parse_expert_key(key)
                    if parsed is None:
                        continue
                    L, E, wname = parsed
                    if skip_existing and store.has((L, E)):
                        continue
                    if wname not in ("w1", "w2", "w3"):
                        continue
                    pending.setdefault((L, E), {})[wname] = f.get_tensor(key)
                    d = pending[(L, E)]
                    if {"w1", "w2", "w3"} <= set(d.keys()):
                        store.put((L, E), d["w1"], d["w3"], d["w2"])
                        pending.pop((L, E))
                        done += 1
                        if done % 64 == 0 or done == target:
                            print(f"  [store] materialized {done}/{target} experts")

        if pending:
            raise RuntimeError(
                f"{len(pending)} experts incomplete: {list(pending)[:3]}...")

    # ----------------------------------------------------------------
    # 通用实现: 构建 MoE 层缓存
    # ----------------------------------------------------------------

    def build_layer_caches(self, store: ExpertSSDStore, device: torch.device,
                           config: OffloadConfig,
                           n_layers: Optional[int] = None
                           ) -> List[LayerExpertCache]:
        """为所有 MoE 层构建 LayerExpertCache。"""
        if n_layers is None:
            n_layers = self.model_spec.n_layers
        caches = []
        for L in range(n_layers):
            ranked = [(L, e) for e in config.get_static_placement(L)]
            cache = LayerExpertCache(
                layer_id=L,
                store=store,
                budget=config.budget,
                device=device,
                config=config,
                ranked_uids=ranked,
            )
            caches.append(cache)
        return caches

    @abstractmethod
    def build_tiered_model(self,
                           state_path: str,
                           store: ExpertSSDStore,
                           device: torch.device,
                           config: OffloadConfig
                           ) -> Tuple[nn.Module, List[LayerExpertCache]]:
        """完整构建三级缓存模型。

        Returns:
          (model, caches): 可直接 .generate() 的模型 + 每层缓存引用。
        """
        ...
