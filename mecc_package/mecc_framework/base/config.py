#!/usr/bin/env python3
"""
mecc_framework.base.config — 统一配置
=====================================
所有模型、硬件、缓存策略的配置类型定义。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class CachePolicy(str, Enum):
    """缓存淘汰/换页策略。"""
    OURS = "ours"          # 三级联合动态 LRU + 升降级
    SWAPMOE = "swapmoe"    # HBM 动态 LRU + CPU 静态
    FIDDLER = "fiddler"    # HBM 常驻 + CPU 上算 (搬激活)
    NAIVE = "naive"        # 不常驻, 每次流式搬运


class QuantPolicy(str, Enum):
    """量化策略。"""
    NONE = "none"          # 全程 fp16 无损 (默认)
    FP8 = "fp8"            # FP8 (未来扩展)
    INT4 = "int4"          # INT4 (未来扩展)


@dataclass
class ExpertSpec:
    """单个 expert 的结构规格 (由模型决定)。"""
    hidden_dim: int
    ffn_dim: int
    nbytes_fp16: int       # 单个 expert 权重总字节数 (w1 + w2 + w3)

    @property
    def size_gb(self) -> float:
        return self.nbytes_fp16 / (1024 ** 3)


@dataclass
class ModelSpec:
    """MoE 模型规格。"""
    name: str
    n_layers: int
    n_experts: int
    top_k: int
    expert_spec: ExpertSpec
    first_moe_layer: int = 0   # 第一个 MoE 层的 layer id (DeepSeek 为 1)

    @property
    def total_expert_gb(self) -> float:
        return self.n_layers * self.n_experts * self.expert_spec.size_gb


@dataclass
class CacheBudget:
    """缓存容量预算 (per-layer)。"""
    k_hbm: int = 0          # HBM 槽数
    k_cpu: int = 0          # CPU 槽数 (SSD 无上限)

    @property
    def total_slots(self) -> int:
        return self.k_hbm + self.k_cpu


@dataclass
class OffloadConfig:
    """完整的 offload 配置 (编译期确定)。"""
    model_spec: ModelSpec
    budget: CacheBudget
    policy: CachePolicy = CachePolicy.OURS
    quant: QuantPolicy = QuantPolicy.NONE
    cold_ssd: bool = True                     # SSD 是否真冷读

    # 编译期 static placement: {layer_id: [expert_id 按热度降序]}
    placement: Dict[int, List[int]] = field(default_factory=dict)

    def get_static_placement(self, layer_id: int) -> List[int]:
        return self.placement.get(layer_id,
                                  list(range(self.model_spec.n_experts)))
