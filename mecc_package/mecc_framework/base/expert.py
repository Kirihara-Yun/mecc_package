#!/usr/bin/env python3
"""
mecc_framework.base.expert — 统一 Expert 权重 (lossless fp16)
==============================================================
组合 mixtral-offloading 的 contiguous UntypedStorage (快速整块搬运)
与 MECC 的 ExpertWeights (无损 SwiGLU 前向), 支持多模型架构。
"""
from __future__ import annotations
import torch
import torch.nn.functional as F
from typing import Tuple


class ExpertWeights:
    """单个 expert 的三权重 + 无损 SwiGLU 前向。

    同时维护 contiguous UntypedStorage 用于快速 H2D 搬运 (继承自
    mixtral-offloading 的 storage 设计), 和独立的 gate/up/down 张量
    用于计算。
    """
    __slots__ = ("w1", "w2", "w3", "_storage", "_offsets", "_dtype")

    def __init__(self, w1: torch.Tensor, w3: torch.Tensor, w2: torch.Tensor):
        """w1: gate_proj [ffn, hidden]
        w3: up_proj   [ffn, hidden]
        w2: down_proj [hidden, ffn]
        """
        self.w1 = w1.clone()
        self.w3 = w3.clone()
        self.w2 = w2.clone()
        self._dtype = w1.dtype
        self._storage = None
        self._offsets = None

    @property
    def device(self) -> torch.device:
        return self.w1.device

    @property
    def dtype(self) -> torch.dtype:
        return self._dtype

    @classmethod
    def from_tensors(cls, gate_proj: torch.Tensor, up_proj: torch.Tensor,
                     down_proj: torch.Tensor) -> "ExpertWeights":
        return cls(gate_proj, up_proj, down_proj)

    def to(self, device: torch.device, non_blocking: bool = False) -> "ExpertWeights":
        """搬移到目标 device, 非阻塞模式下利用 CUDA copy engine。"""
        return ExpertWeights(
            self.w1.to(device, non_blocking=non_blocking),
            self.w3.to(device, non_blocking=non_blocking),
            self.w2.to(device, non_blocking=non_blocking),
        )

    def cpu(self) -> "ExpertWeights":
        return ExpertWeights(self.w1.cpu(), self.w3.cpu(), self.w2.cpu())

    def pin_memory(self) -> "ExpertWeights":
        """CPU pinned memory, 加速 H2D 拷贝 (仅 CUDA 有效)。"""
        if torch.cuda.is_available() and self.w1.device.type == "cpu":
            return ExpertWeights(
                self.w1.pin_memory(), self.w3.pin_memory(), self.w2.pin_memory()
            )
        return self

    def build_storage(self, device: torch.device = torch.device("cpu")) -> "ExpertWeights":
        """构建 contiguous UntypedStorage (整块搬运用), 放在指定 device 上。

        与 mixtral-offloading 的 replace_layer_storage 概念一致:
        将三权重连续拼接为单块内存, 支持整块 H2D 搬运。
        """
        nbytes = self.nbytes()
        storage = torch.UntypedStorage(nbytes, device=device)

        offset = 0
        offsets = []
        for w in (self.w1, self.w3, self.w2):
            n = w.nbytes if hasattr(w, "nbytes") else w.element_size() * w.nelement()
            view = torch.as_tensor(storage[offset:offset + n],
                                   dtype=w.dtype, device=device).view(w.shape)
            view.copy_(w.to(device))
            offsets.append(offset)
            offset += n

        self._storage = storage
        self._offsets = offsets
        return self

    @classmethod
    def from_storage(cls, storage: torch.UntypedStorage, shapes: Tuple,
                     dtype: torch.dtype = torch.float16) -> "ExpertWeights":
        """从 contiguous storage 重建 ExpertWeights (零拷贝 view)。"""
        off = 0
        ws = []
        for sh in shapes:
            n = int(torch.prod(torch.tensor(sh))) * dtype.itemsize
            view = torch.as_tensor(storage[off:off + n],
                                   dtype=dtype).view(sh)
            ws.append(view)
            off += n

        ret = cls(ws[0], ws[1], ws[2])
        ret._storage = storage
        return ret

    def get_storage(self) -> torch.UntypedStorage:
        """返回存储 (如未构建则自动构建到 CPU)。"""
        if self._storage is None:
            self.build_storage()
        return self._storage

    def nbytes(self) -> int:
        return self.w1.nbytes + self.w3.nbytes + self.w2.nbytes

    def __call__(self, x: torch.Tensor) -> torch.Tensor:
        """无损 SwiGLU 前向, 在权重所在 device 上计算。

        自动将 x 转换为权重 dtype (支持 fp32 模型 + fp16 权重的混合精度场景)。
        """
        w_dtype = self.w1.dtype
        if x.dtype != w_dtype:
            x = x.to(w_dtype)
        return (F.silu(x @ self.w1.t()) * (x @ self.w3.t())) @ self.w2.t()

    def to_tuple(self) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return (self.w1, self.w3, self.w2)


# 已知模型架构的 expert 权重 shapes
EXPERT_SHAPES: dict = {
    "mixtral":   [(14336, 4096), (14336, 4096), (4096, 14336)],   # w1, w3, w2
    "deepseek":  [(2048, 576),  (2048, 576),  (576, 2048)],       # DeepSeek-V2-Lite
    "qwen_moe":  [(5632, 2560), (5632, 2560), (2560, 5632)],      # Qwen2-MoE
}
