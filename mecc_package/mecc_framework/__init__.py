#!/usr/bin/env python3
"""
mecc_framework — 通用 MoE 推理框架 (基于 mixtral-offloading 改造)
==================================================================
支持多模型架构 (Mixtral / DeepSeek / 可扩展) + 三级无损缓存 (HBM / CPU / SSD)。

改造来源:
  保留 mixtral-offloading 的 contiguous UntypedStorage 权重打包、per-layer LRU 淘汰组、
  异步 non-blocking swap 三个核心设计。
  去除 HQQ 2-bit 量化, 改为全程 fp16 无损推理。
  新增 SSD 第三级缓存, 抽象策略接口 (ours / swapmoe / fiddler / naive)。
"""
"""mecc_framework — Universal MoE inference framework with tiered caching."""
