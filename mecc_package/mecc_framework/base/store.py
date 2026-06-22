#!/usr/bin/env python3
"""
mecc_framework.base.store — SSD Expert 冷存
============================================
每个 expert 一个 .bin 文件 (w1|w3|w2 顺序拼接)。
fadvise/F_NOCACHE 保证真实 NVMe 冷读延迟, 避开 page cache。
"""
from __future__ import annotations
import os
import sys
import fcntl
import numpy as np
import torch
from typing import Dict, Optional, Tuple

from .expert import ExpertWeights

ExpertUID = Tuple[int, int]            # (layer_id, expert_idx)
IS_DARWIN = sys.platform == "darwin"
F_NOCACHE = 48                         # macOS fcntl: 绕过 unified buffer cache


class ExpertSSDStore:
    """Expert 权重持久化到 NVMe SSD (任意架构通用)。

    存储格式: 每个 expert 一个 .bin, 顺序写入 w1|w3|w2 的 fp16 raw bytes。
    读取支持真冷读 (fadvise DONTNEED / F_NOCACHE) 和热读 (page cache 命中)。
    """

    def __init__(self, root: str, hidden_dim: int, ffn_dim: int,
                 dtype: torch.dtype = torch.float16, model_type: str = "generic"):
        self.root = root
        os.makedirs(root, exist_ok=True)
        self.hidden_dim = hidden_dim
        self.ffn_dim = ffn_dim
        self.dtype = dtype
        self.model_type = model_type

        # shapes: w1 [ffn, hidden], w3 [ffn, hidden], w2 [hidden, ffn]
        self.shapes = [(ffn_dim, hidden_dim), (ffn_dim, hidden_dim), (hidden_dim, ffn_dim)]
        self.counts = [int(np.prod(s)) for s in self.shapes]
        self.itemsize = {torch.float16: 2, torch.float32: 4,
                         torch.bfloat16: 2}[dtype]
        self.np_dtype = {torch.float16: np.float16, torch.float32: np.float32,
                         torch.bfloat16: np.float16}[dtype]
        self.nbytes = [c * self.itemsize for c in self.counts]
        self.total_bytes = sum(self.nbytes)
        self._paths: Dict[ExpertUID, str] = {}

        print(f"  [store] init {model_type}, expert size: {self.total_bytes/1024/1024:.1f}MB")

    def path(self, uid: ExpertUID) -> str:
        return os.path.join(self.root, f"L{uid[0]}_E{uid[1]}.bin")

    def has(self, uid: ExpertUID) -> bool:
        p = self.path(uid)
        return os.path.exists(p) and os.path.getsize(p) == self.total_bytes

    def put(self, uid: ExpertUID, w1: torch.Tensor, w3: torch.Tensor,
            w2: torch.Tensor) -> None:
        """将 expert 写入磁盘 (幂等)。"""
        p = self.path(uid)
        if self.has(uid):
            self._paths[uid] = p
            return
        with open(p, "wb") as f:
            for w in (w1, w3, w2):
                f.write(w.detach().float().cpu().numpy()
                        .astype(self.np_dtype, copy=False).tobytes())
        self._paths[uid] = p

    def put_expert_weights(self, uid: ExpertUID, ws: ExpertWeights) -> None:
        """从 ExpertWeights 直接落盘。"""
        self.put(uid, ws.w1, ws.w3, ws.w2)

    def _read_cold(self, path: str, nb: int) -> bytes:
        """绕过 page cache 的真冷读。"""
        fd = os.open(path, os.O_RDONLY)
        try:
            if IS_DARWIN:
                fcntl.fcntl(fd, F_NOCACHE, 1)
            elif hasattr(os, "posix_fadvise"):
                os.posix_fadvise(fd, 0, nb, os.POSIX_FADV_DONTNEED)
            buf = bytearray()
            while len(buf) < nb:
                chunk = os.read(fd, nb - len(buf))
                if not chunk:
                    break
                buf += chunk
            return bytes(buf)
        finally:
            if (not IS_DARWIN) and hasattr(os, "posix_fadvise"):
                os.posix_fadvise(fd, 0, nb, os.POSIX_FADV_DONTNEED)
            os.close(fd)

    def load_to_cpu(self, uid: ExpertUID, cold: bool = True) -> ExpertWeights:
        """从 SSD 加载 expert 到 CPU。cold=True 时真冷读。"""
        p = self.path(uid)
        if cold:
            raw = self._read_cold(p, self.total_bytes)
            ws = []
            off = 0
            for sh, cnt, nb in zip(self.shapes, self.counts, self.nbytes):
                arr = np.frombuffer(raw, dtype=self.np_dtype,
                                    count=cnt, offset=off).reshape(sh)
                ws.append(torch.from_numpy(arr.copy()).to(self.dtype))
                off += nb
        else:
            ws = []
            with open(p, "rb") as f:
                for sh, cnt in zip(self.shapes, self.counts):
                    arr = np.fromfile(f, dtype=self.np_dtype, count=cnt).reshape(sh)
                    ws.append(torch.from_numpy(arr.copy()).to(self.dtype))
        return ExpertWeights(ws[0], ws[1], ws[2])
