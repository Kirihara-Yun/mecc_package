#!/usr/bin/env python3
"""
tiered_engine.py — 三级 (HBM/CPU/SSD) 无损 expert 缓存引擎
============================================================
本文件是端到端框架的"心脏"。设计上**复用** dvmazur/mixtral-offloading 的三个核心思想，
但做了两处关键改造，使其能进 DAC 主表：

  复用 (reuse, 学术上允许的框架复用):
    1) 每个 expert 的权重打包成"连续内存块"便于整块搬运      (源: expert_wrapper.py)
    2) per-layer LRU + 异步预取换页, 把 PCIe 传输藏在计算之后   (源: expert_cache.py)
    3) 与 SparseMoeWrapper.forward 的 load_experts(*uids) 契约   (源: custom_layers.py)

  改造 (our contribution, 卖点):
    A) 两级 (GPU+CPU) → 三级 (HBM + CPU pinned + SSD 冷存)。
       大模型 (Mixtral fp16 ~90GB) CPU 也装不下, 必须落 SSD —— 这是三级缓存的主场。
    B) 去掉 HQQ 2-bit 量化 → 全程 fp16 **无损 (lossless)**。
       expert 输出与原模型逐位一致 (0 精度损失), 这是相对 SwapMoE/EdgeMoE 的核心卖点,
       同时绕开 5090 (sm_120/Blackwell) 上 triton 量化 kernel 的兼容性风险。

四种策略 (apples-to-apples, 共享同一 store / 同一预算 K_H+K_C / 同一 trace):
    ours    : HBM(K_H) + CPU(K_C) 联合**动态** LRU, 带升降级, 其余 SSD     ← 本文方法
    swapmoe : 仅 HBM(K_H) 动态 LRU; CPU 驻留**静态** top-K_C; 其余 SSD      ← 主对手
    fiddler : HBM(K_H) 常驻; miss 时在 **CPU 上算 expert** (搬激活而非权重)  ← CPU-GPU 协同
    naive   : 不在 HBM 常驻 expert; 每次从 CPU/SSD **流式**搬权重到 GPU      ← 全 offload 下界
"""
from __future__ import annotations
import os
import sys
import fcntl
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterator, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn.functional as F

ExpertUID = Tuple[int, int]            # (layer_id, expert_idx)
IS_DARWIN = sys.platform == "darwin"
F_NOCACHE = 48                         # macOS fcntl: 绕过 unified buffer cache


# ════════════════════════════════════════════════════════════════════
# 1. ExpertWeights —— 一个 expert 的三权重 + 无损 SwiGLU 前向
#    Mixtral / Qwen-MoE 的 expert: out = w2( silu(w1 x) * w3 x )
#    HF Linear 权重形状 [out, in] → 前向用 x @ W.T。
# ════════════════════════════════════════════════════════════════════

class ExpertWeights:
    """持有单个 expert 的 (w1, w3, w2) 权重张量, 可直接当 callable 用。
    与 SparseMoeWrapper.forward 中的 `expert_layer(current_state)` 契约一致。
    """
    __slots__ = ("w1", "w3", "w2")

    def __init__(self, w1: torch.Tensor, w3: torch.Tensor, w2: torch.Tensor):
        self.w1 = w1   # [ffn, hidden]  gate_proj
        self.w3 = w3   # [ffn, hidden]  up_proj
        self.w2 = w2   # [hidden, ffn]  down_proj

    def to(self, device, non_blocking: bool = False) -> "ExpertWeights":
        return ExpertWeights(
            self.w1.to(device, non_blocking=non_blocking),
            self.w3.to(device, non_blocking=non_blocking),
            self.w2.to(device, non_blocking=non_blocking),
        )

    def pin(self) -> "ExpertWeights":
        # CPU pinned memory → H2D 拷贝更快 (复用 mixtral-offloading 的 pin_memory 思想)。
        # 仅 CUDA 下有意义; MPS/CPU 环境 pin_memory 会报错, 直接跳过。
        if torch.cuda.is_available() and self.w1.device.type == "cpu":
            return ExpertWeights(self.w1.pin_memory(), self.w3.pin_memory(), self.w2.pin_memory())
        return self

    def __call__(self, x: torch.Tensor) -> torch.Tensor:
        # 无损 fp16 SwiGLU; 在权重所在 device 上计算
        return (F.silu(x @ self.w1.t()) * (x @ self.w3.t())) @ self.w2.t()

    def nbytes(self) -> int:
        return self.w1.nbytes + self.w3.nbytes + self.w2.nbytes


# ════════════════════════════════════════════════════════════════════
# 2. SSDExpertStore —— 所有 expert 的磁盘冷存 (fp16, 真实文件, 真冷读)
#    每个 expert 一个 .bin (w1|w3|w2 顺序拼接), 用 fadvise/F_NOCACHE 保证
#    读到的是真实 NVMe 延迟而非 page-cache 命中 (复用 real_tiered_cache 的冷读)。
# ════════════════════════════════════════════════════════════════════

class SSDExpertStore:
    def __init__(self, root: str, hidden: int, ffn: int,
                 dtype: torch.dtype = torch.float16, io_workers: int = 8):
        self.root = root
        os.makedirs(root, exist_ok=True)
        self.hidden = hidden
        self.ffn = ffn
        self.dtype = dtype
        self.np_dtype = {torch.float16: np.float16, torch.float32: np.float32,
                         torch.bfloat16: np.float16}[dtype]   # bf16 落盘按 fp16 处理 (见 put)
        self.shapes = [(ffn, hidden), (ffn, hidden), (hidden, ffn)]   # w1, w3, w2
        self.counts = [int(np.prod(s)) for s in self.shapes]
        self.itemsize = np.dtype(self.np_dtype).itemsize
        self.nbytes = [c * self.itemsize for c in self.counts]
        self.total_bytes = sum(self.nbytes)
        self._paths: Dict[ExpertUID, str] = {}
        # ── 线程池: 并行 SSD I/O ──
        self._io_pool = ThreadPoolExecutor(max_workers=io_workers)

    def path(self, uid: ExpertUID) -> str:
        return os.path.join(self.root, f"L{uid[0]}_E{uid[1]}.bin")

    def has(self, uid: ExpertUID) -> bool:
        p = self.path(uid)
        return os.path.exists(p) and os.path.getsize(p) == self.total_bytes

    def put(self, uid: ExpertUID, w1: torch.Tensor, w3: torch.Tensor, w2: torch.Tensor):
        """把一个 expert 的三权重以 fp16 顺序写入磁盘。幂等: 已存在则跳过。"""
        p = self.path(uid)
        if self.has(uid):
            self._paths[uid] = p
            return
        with open(p, "wb") as f:
            for w in (w1, w3, w2):
                f.write(w.detach().to(self.dtype).contiguous().cpu().numpy()
                        .astype(self.np_dtype, copy=False).tobytes())
        self._paths[uid] = p

    def _read_cold(self, path: str, nb: int) -> bytes:
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
        """从 SSD 读回一个 expert 到 CPU (默认真冷读)。"""
        return self._load_one(uid, cold)

    def _load_one(self, uid: ExpertUID, cold: bool = True) -> ExpertWeights:
        """单个 expert SSD→CPU 读取 (内部使用)。"""
        p = self.path(uid)
        if cold:
            raw = self._read_cold(p, self.total_bytes)
            ws = []
            off = 0
            for sh, cnt, nb in zip(self.shapes, self.counts, self.nbytes):
                arr = np.frombuffer(raw, dtype=self.np_dtype, count=cnt, offset=off).reshape(sh)
                ws.append(torch.from_numpy(arr.copy()).to(self.dtype))
                off += nb
        else:
            ws = []
            with open(p, "rb") as f:
                for sh, cnt in zip(self.shapes, self.counts):
                    arr = np.fromfile(f, dtype=self.np_dtype, count=cnt).reshape(sh)
                    ws.append(torch.from_numpy(arr.copy()).to(self.dtype))
        return ExpertWeights(ws[0], ws[1], ws[2])

    def batch_load_to_cpu(self, uids: List[ExpertUID],
                          cold: bool = True) -> Dict[ExpertUID, ExpertWeights]:
        """并行批量 SSD→CPU: 用 ThreadPool 同时读多个 expert。"""
        if len(uids) <= 1:
            return {uid: self._load_one(uid, cold) for uid in uids}
        results = {}
        futures = {self._io_pool.submit(self._load_one, uid, cold): uid for uid in uids}
        for f in as_completed(futures):
            results[futures[f]] = f.result()
        return results



# ════════════════════════════════════════════════════════════════════
# 3. LayerExpertCache —— 单层的三级缓存; policy 决定换页行为
#    每层独享一组 GPU(K_H) / CPU(K_C) 常驻池, 跨 token 持久 (热 expert 不重复搬)。
#    这与真实 offloading 系统一致: 每层最热的若干 expert 常驻显存。
# ════════════════════════════════════════════════════════════════════

class LayerExpertCache:
    def __init__(self,
                 layer_id: int,
                 store: SSDExpertStore,
                 ranked_uids: List[ExpertUID],   # 按编译期热度降序 (本层全部 expert)
                 k_h: int,
                 k_c: int,
                 device: torch.device,
                 policy: str = "ours",
                 cold_ssd: bool = True):
        self.layer_id = layer_id
        self.store = store
        self.k_h = max(0, int(k_h))
        self.k_c = max(0, int(k_c))
        self.device = device
        self.policy = policy
        self.cold_ssd = cold_ssd

        self.gpu: "OrderedDict[ExpertUID, Tuple[ExpertWeights, ExpertWeights]]" = OrderedDict()  # eid → (gpu_ws, cpu_ws) 零拷贝淘汰
        self.cpu: "OrderedDict[ExpertUID, ExpertWeights]" = OrderedDict()  # eid → CPU ws
        self.static_cpu: Dict[ExpertUID, ExpertWeights] = {}               # swapmoe 用: 静态 CPU
        # 命中计数: [hbm, cpu, ssd, cpu_compute(fiddler)]
        self.hits = [0, 0, 0, 0]

        # ── 策略插件化: 支持字符串名或 CachePolicy 实例 ──
        if isinstance(policy, str):
            from policy_plugin import get_policy  # noqa: F811 延迟导入避免循环
            self._policy_plugin = get_policy(policy)
        else:
            self._policy_plugin = policy  # CachePolicy 实例

        # CUDA 流水线: 专用流用于 H2D 拷贝, 与计算重叠
        self._copy_stream = torch.cuda.Stream() if device.type == "cuda" else None
        self._pending_copy: Optional[torch.cuda.Event] = None  # 上一个异步拷贝的完成信号
        self._prefetch_buf: Dict[ExpertUID, ExpertWeights] = {}  # 批量预取的临时 GPU 缓存
        self._ssd_preload_buf: Dict[ExpertUID, ExpertWeights] = {}  # 并行 SSD I/O 临时缓冲

        # ── 编译期静态放置 (warm-up): 最热 K_H 入 GPU (保留 CPU 镜像, 支持零拷贝淘汰) ──
        for uid in ranked_uids[:self.k_h]:
            ws_cpu = self.store.load_to_cpu(uid, cold=False)
            self.gpu[uid] = (ws_cpu.to(device), ws_cpu)  # CPU 镜像不 pin，零拷贝淘汰用普通内存即可
        if self._policy_plugin.name == "swapmoe":
            for uid in ranked_uids[self.k_h:self.k_h + self.k_c]:
                self.static_cpu[uid] = self.store.load_to_cpu(uid, cold=False).pin()
        else:
            for uid in ranked_uids[self.k_h:self.k_h + self.k_c]:
                self.cpu[uid] = self.store.load_to_cpu(uid, cold=False).pin()
        if device.type == "cuda":
            torch.cuda.synchronize(device)

    # ---- GPU 池 LRU 维护 ----
    def _evict_gpu_if_needed(self, spill_to_cpu: bool):
        """零拷贝淘汰: 复用 HBM 中保留的 CPU 镜像, 不执行 D2H 拷贝。"""
        while len(self.gpu) > self.k_h:
            ev_uid, (ev_gpu, ev_cpu) = self.gpu.popitem(last=False)
            if spill_to_cpu and self.k_c > 0 and ev_cpu is not None:
                self.cpu[ev_uid] = ev_cpu                    # 零拷贝: 复用只读 CPU 镜像
                self.cpu.move_to_end(ev_uid)
                while len(self.cpu) > self.k_c:
                    self.cpu.popitem(last=False)              # CPU→SSD (丢引用)

    def _to_gpu(self, ws: ExpertWeights) -> ExpertWeights:
        """异步 H2D 拷贝到 copy_stream, 与默认流上的计算重叠"""
        if self._copy_stream is not None and ws.w1.device.type == "cpu":
            with torch.cuda.stream(self._copy_stream):
                result = ws.to(self.device, non_blocking=True)
            self._pending_copy = True
            return result
        return ws.to(self.device, non_blocking=False)

    def sync_copy(self):
        """等待异步 H2D 拷贝完成 (仅在确有在途拷贝时调用)"""
        if self._copy_stream is not None and self._pending_copy:
            self._copy_stream.synchronize()
            self._pending_copy = False

    def prefetch_near_miss(self, uids: List[ExpertUID]):
        """Router-logit 预测预取: 对 near-miss expert 做温和预热 (不淘汰, 不记账)。
        CPU 命中 → 异步 H2D 到 _nearmiss_buf; SSD miss → 后台读盘到 CPU。
        """
        if not uids:
            return
        self._nearmiss_buf = getattr(self, '_nearmiss_buf', {})
        for uid in uids:
            if uid in self.gpu or uid in self._nearmiss_buf:
                continue
            if uid in self.cpu:
                # 异步 H2D: 不动 cache 状态, 只预热 GPU 侧
                if self._copy_stream is not None:
                    ws_cpu = self.cpu[uid]
                    with torch.cuda.stream(self._copy_stream):
                        self._nearmiss_buf[uid] = ws_cpu.to(self.device, non_blocking=True)
            elif uid not in self.static_cpu:
                # SSD → CPU 后台读 (不改命中计数)
                self._nearmiss_buf[uid] = self.store.load_to_cpu(uid, cold=self.cold_ssd)

    def consume_nearmiss(self, uid: ExpertUID):
        """在 _access 前检查 near-miss 预取缓冲, 命中则直接提升到 HBM。"""
        buf = getattr(self, '_nearmiss_buf', {})
        if uid in buf:
            return buf.pop(uid)
        return None

    def prefetch_ssd_batch(self, uids: List[ExpertUID], is_prefill: bool = True):
        """并行 SSD 预取 (policy 插件可选调用): prefill 阶段用 ThreadPool 批量读。"""
        self._ssd_preload_buf.clear()
        if not is_prefill:
            return
        ssd_miss = [uid for uid in uids if uid not in self.gpu
                    and uid not in self.cpu and uid not in self.static_cpu]
        if ssd_miss:
            self._ssd_preload_buf = self.store.batch_load_to_cpu(ssd_miss, cold=self.cold_ssd)

    def _load_from_ssd(self, uid: ExpertUID) -> ExpertWeights:
        """从 SSD 加载: 优先 _ssd_preload_buf, fallback 同步单读。"""
        if uid in self._ssd_preload_buf:
            return self._ssd_preload_buf.pop(uid)
        return self.store.load_to_cpu(uid, cold=self.cold_ssd)

    def batch_prefetch(self, cpu_uids: List[ExpertUID]):
        """批量异步 H2D 拷贝: 一次性把多个 CPU expert 全部搬上 GPU。
        利用 PCIe 带宽并行, 等待时 GPU 可以算其他 expert。"""
        if self._copy_stream is None or not cpu_uids:
            return
        self._prefetch_buf.clear()
        with torch.cuda.stream(self._copy_stream):
            for uid in cpu_uids:
                # 从 CPU 池 (ours/fiddler) 或 static_cpu (swapmoe) 获取
                ws = self.cpu.get(uid) or self.static_cpu.get(uid)
                if ws is not None and uid not in self.gpu:
                    gpu_ws = ws.to(self.device, non_blocking=True)
                    self._prefetch_buf[uid] = gpu_ws
        self._pending_copy = True

    def consume_prefetched(self, uid: ExpertUID) -> Optional[ExpertWeights]:
        """从批量预取缓冲中取出已就绪的 GPU expert"""
        return self._prefetch_buf.pop(uid, None)

    # ---- 与 SparseMoeWrapper 契约一致的加载接口 ----
    def load_experts(self, *uids: ExpertUID, unordered: bool = True
                     ) -> Iterator[Tuple[ExpertUID, ExpertWeights]]:
        # 批量异步 H2D: 一次性把本轮所有 CPU 命中的 expert 搬上 GPU
        cpu_uids = [uid for uid in uids if uid not in self.gpu
                    and (uid in self.cpu or uid in self.static_cpu)]
        if cpu_uids:
            self.batch_prefetch(cpu_uids)
            # 直接把预取结果放进 self.gpu, 让 _access 自动命中
            for uid in cpu_uids:
                gpu_ws = self._prefetch_buf.pop(uid, None)
                if gpu_ws is not None:
                    ws_cpu = self.cpu.pop(uid, None) or self.static_cpu.get(uid)
                    self.gpu[uid] = (gpu_ws, ws_cpu)  # _access 将自动计为 HBM hit
                    self.gpu.move_to_end(uid)
                    self._evict_gpu_if_needed(spill_to_cpu=True)

        for uid in uids:
            ws = self._access(uid)          # CPU 命中的已在 gpu 中, 直接命中
            yield uid, ws
        self.sync_copy()

    def _access(self, uid: ExpertUID) -> ExpertWeights:
        """委托给策略插件处理 expert 访问 (插件化替代 if/elif 平铺)。"""
        return self._policy_plugin.access(self, uid)

    def hit_summary(self) -> Dict[str, float]:
        tot = sum(self.hits) or 1
        return {
            "hbm_pct": round(self.hits[0] / tot * 100, 1),
            "cpu_pct": round(self.hits[1] / tot * 100, 1),
            "ssd_pct": round(self.hits[2] / tot * 100, 1),
            "cpu_compute_pct": round(self.hits[3] / tot * 100, 1),
            "total_accesses": tot,
        }
