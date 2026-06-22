#!/usr/bin/env python3
"""
mecc_framework.models — 模型适配器
====================================
每个模型架构一个适配器, 负责:
  1) weight 命名解析 (从 safetensors key 识别 expert 权重)
  2) 模型加载 + MoE 层替换
  3) 模型结构参数 (hidden_dim, ffn_dim, n_experts 等)

已支持:
  - Mixtral (mistralai/Mixtral-8x7B)
  - DeepSeek (deepseek-ai/DeepSeek-V2-Lite)

扩展新模型: 实现同名接口即可。
"""
from .base import ModelAdapter
from .mixtral import MixtralAdapter
from .deepseek import DeepSeekAdapter

# 模型名 → adapter 类
REGISTRY = {
    "mixtral": MixtralAdapter,
    "deepseek": DeepSeekAdapter,
}

# HF model_id → adapter 类型
MODEL_TYPE_MAP = {
    "mistralai/Mixtral-8x7B-Instruct-v0.1": "mixtral",
    "mistralai/Mixtral-8x7B-v0.1": "mixtral",
    "deepseek-ai/DeepSeek-V2-Lite": "deepseek",
}


def get_adapter(model_id: str, **kwargs):
    """根据模型 ID 或架构类型获取对应的 adapter。"""
    mtype = MODEL_TYPE_MAP.get(model_id, model_id)
    adapter_cls = REGISTRY.get(mtype)
    if adapter_cls is None:
        raise ValueError(f"Unknown model type: {mtype}. "
                         f"Available: {list(REGISTRY.keys())}")
    return adapter_cls(model_id, **kwargs)
