#!/usr/bin/env python3
"""
mecc_framework.cache.swap — 异步搬运引擎
==========================================
mixtral-offloading 的异步 non-blocking swap 模式:
  - 专用 copy_stream (CUDA) 用于 H2D 搬运, 与计算流重叠
  - UngtpedStorage 整块搬运, 多 expert 批量预取
  - buffer pool 减少临时内存分配
"""
from __future__ import annotations
import torch
from collections import deque
from typing import Optional, Dict, List, Tuple

from ..base.expert import ExpertWeights

ExpertUID = Tuple[int, int]


class AsyncSwapEngine:
    """管理 PCIe 搬运流水线, 支持多 expert 批量异步预取。

    核心思想 (来自 mixtral-offloading):
      - 一个 expert 的权重打成一个 contiguous UntypedStorage
      - H2D 在独立 copy_stream 上 non-blocking, 与计算重叠
      - 预留 buffer pool 避免搬运时的临时内存分配
    """

    def __init__(self, device: torch.device, buffer_count: int = 4):
        self.device = device
        self.buffer_count = buffer_count
        self._copy_stream: Optional[torch.Stream] = None
        if device.type == "cuda":
            self._copy_stream = torch.cuda.Stream()

        # Buffer pool: 临时存放搬运到 GPU 的 expert
        self._gpu_buffers: deque = deque()
        self._pending_events: deque = deque()

        # 批量预取缓冲
        self._prefetch_buf: Dict[ExpertUID, ExpertWeights] = {}

    def allocate_buffers(self, expert_bytes: int, dtype: torch.dtype = torch.float16):
        """预先分配 buffer pool (每个 buffer 存一个 expert 的全部权重)。"""
        for _ in range(self.buffer_count):
            storage = torch.UntypedStorage(expert_bytes, device=self.device)
            # 计算对应的 shapes
            self._gpu_buffers.append(storage)

    def copy_to_gpu(self, ws: ExpertWeights, non_blocking: bool = True
                    ) -> ExpertWeights:
        """搬运 ExpertWeights 到 GPU。

        non_blocking=True: 在 copy_stream 上异步搬运, 立即返回。
        non_blocking=False: 同步搬运 (用于首次 warmup 或 MPS CPU 环境)。
        """
        if ws.device.type == "cpu" and self._copy_stream is not None and non_blocking:
            with torch.cuda.stream(self._copy_stream):
                result = ws.to(self.device, non_blocking=True)
            return result
        return ws.to(self.device, non_blocking=non_blocking and ws.device.type == "cpu")

    def batch_prefetch(self, uids_to_ws: Dict[ExpertUID, ExpertWeights]):
        """批量异步预取: 一次性把多个 CPU expert 全部搬上 GPU (并行利用 PCIe 带宽)。"""
        if self._copy_stream is None or not uids_to_ws:
            return
        self._prefetch_buf.clear()
        with torch.cuda.stream(self._copy_stream):
            for uid, ws in uids_to_ws.items():
                gpu_ws = ws.to(self.device, non_blocking=True)
                self._prefetch_buf[uid] = gpu_ws

    def consume_prefetched(self, uid: ExpertUID) -> Optional[ExpertWeights]:
        """取出已在预取缓冲中的 GPU expert。"""
        return self._prefetch_buf.pop(uid, None)

    def has_pending_prefetch(self) -> bool:
        return len(self._prefetch_buf) > 0

    def sync_copy(self):
        """等待所有在途的异步搬运完成。"""
        if self._copy_stream is not None:
            self._copy_stream.synchronize()

    def sync_device(self):
        """设备级同步。"""
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
        elif self.device.type == "mps":
            torch.mps.synchronize()
