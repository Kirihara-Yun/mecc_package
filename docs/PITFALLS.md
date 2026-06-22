# 实验踩坑记录

> 本文件记录 MECC 端到端实验中的常见问题和解决方案。
> 每次遇到新坑追加一条，不覆盖旧条目。

---

## 1. 环境与硬件

### 1.1 K_H=4 OOM 在 A100 上（torch 2.5.1+cu121）

**现象**：`HBM_budget=50`（K_H=4）时 `build_tiered_model` 构建成功（~67GB），但推理时 `batch_prefetch` 阶段 OOM。
```
torch.OutOfMemoryError: ... 79.12 GiB in use ...
  at ExpertWeights.to() → w1.to(device, non_blocking=...)
```

**原因**：torch 2.5.1+cu121 比之前版本多占用 ~2GB 推理内存，A100 PCIe 79.25GiB 实际可用不足。

**解决**：降到 HBM=30（K_H=2），GPU 峰值 ~75GB 稳定通过。
- 原始代码同样 OOM（`git stash` + 原始 `run_e2e.py` 复现确认）
- 不是代码 bug，是环境版本差异

### 1.2 `expandable_segments:True` 不一定有帮助

**现象**：加了 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` 反而 OOM 更多。

**结论**：不加更好。默认 PyTorch 内存分配器在这个场景下表现不错。

### 1.3 WikiText-2 联网失败

**现象**：无外网环境 `datasets.load_dataset("wikitext")` 报 `ConnectionResetError`。

**影响**：不影响实验——`run_e2e.py` 自动回退到内置 prompts，PPL 用内置 prompt 计算。

---

## 2. 多进程冲突

### 2.1 同一时间只能跑一个实验

**现象**：两个 `run_e2e.py` 同时运行 → GPU 各占 ~33GB → 都 OOM 或死锁（Dl 状态）。

**规则**：**绝对不要同时跑两个实验**。一个实验结束再跑下一个。

### 2.2 杀掉旧进程后再跑新实验

```bash
kill <pid> 2>/dev/null
sleep 2
# 确认干净
ps aux | grep run_e2e | grep -v grep || echo "CLEAN"
# 再启动新实验
```

---

## 3. 性能陷阱

### 3.1 batch_prefetch 不能随意限制

**现象**：我在 `tiered_engine.py` 加了 `cpu_uids = cpu_uids[:max(0, gpu_avail)]` 想防止 OOM，
结果 GPU 满了后 `gpu_avail=0` → 所有 CPU expert 改成同步单读 → **100× 变慢**。

**正解**：K_H=2 时 GPU 基底 ~44GB，每层 batch_prefetch 最多额外 6GB，峰值 ~50GB < 80GB——原始代码不会 OOM，不需要限制。

**教训**：先在纸上算峰值内存再动手改。

### 3.2 冷 SSD 是真实瓶颈，不是 bug

**现象**：Mixtral 0.04 tok/s 看起来很慢。

**原因**：每个 SSD miss 读 1GB，300MB/s → 3.3s/miss。K_H=2 下 18% SSD 命中率，每个 token 触发 ~11 次 SSD miss。

**这不是 bug**——这就是 MECC 主战场的物理极限。想要快速迭代可以：
- `--warm_ssd`（利用 page cache，快 10-100×，仅用于调试）
- `--max_new_tokens 4 --n_prompts 1`（极简参数快速验证）

### 3.3 PyTorch 输出缓冲

**现象**：`nohup python3 run_e2e.py > log 2>&1 &` 后半天看不到输出。

**解决**：加 `PYTHONUNBUFFERED=1` 或 `python3 -u`。

---

## 4. 编译参数

### 4.1 `--uniform` vs per_layer_adaptive

**现象**：`run_e2e.py` 默认生成随机 `per_layer_alpha` → `compile_plan` 使用水塘分配 → HBM slots 可能比统一分配多 ~20%。

**影响**：K_H=4 时水塘分配可能给 152 HBM slots（51GB），vs 统一分配 128 slots（43GB）。

**建议**：
- 与之前 A100 实验对齐：用 `--uniform` 统一分配
- 需要 per-layer 自适应时用 `--profile` 传入真实 profile 数据

### 4.2 store_root 选用

- 实验结束后 store 可以复用（`--store_root` 指向同一目录跳过物化）
- 换 HBM 预算时建议换 store，避免旧预算下的 placement 残留

---

## 5. 优化尝试与失败记录

### 5.1 M1 async_ssd_read 尝试失败

**改动**：`load_experts` 中提前用 ThreadPool 发起 SSD 读，
CPU/HBM 处理时后台读盘，期望 overlap。

**结果**：DeepSeek 上 0.83 tok/s vs 基线 1.14 tok/s（**-27%**）。

**原因**：DeepSeek 专家小（16.5MB，~50ms SSD 读），
ThreadPool 提交/等待开销 > 收益。Mixtral 专家大（336MB，~3.3s）可能受益，
但 ThreadPool 的 future 等待仍是同步阻塞点。

**后续方向**：需要更激进的异步（专用 I/O 线程 + 完成回调），
且应按 expert 大小自适应触发。

---

## 6. 数值异常

### 5.1 SwapMoE PPL=91 异常（DeepSeek）

**现象**：DeepSeek L1 实验中 SwapMoE PPL=91，OURS/fiddler 均为 ~44。

**状态**：未排查。可能原因：静态 CPU 池导致的数值路径差异、或 warmup forward 影响。

**临时处理**：标记为 anomaly，只看 tok/s 和命中率对比。

---

## 6. 提速方案

### 日常开发 / 快速验证

```bash
# 极简参数（5-10 分钟）
--prompt_len 16 --max_new_tokens 4 --n_prompts 2 --skip_ppl --policies ours

# warm SSD（利用页缓存，快 10-100×）
--warm_ssd --prompt_len 16 --max_new_tokens 4 --n_prompts 2 --skip_ppl
```

### 正式实验

```bash
# L1 DeepSeek（快，~25 分钟 4 策略）
--hbm_budget 8 --cpu_budget 12 --alpha 0.73 \
--prompt_len 64 --max_new_tokens 64 --n_prompts 8

# L2 Mixtral（慢，K_H=2 约 2 小时 2 策略）
--hbm_budget 30 --cpu_budget 40 --uniform \
--prompt_len 32 --max_new_tokens 16 --n_prompts 4
```

### 更激进的提速（需验证安全性）

1. **M1 `async_ssd_read`**：SSD 读与计算 overlap，隐藏冷读延迟
2. **并发 SSD 读**：`SSDExpertStore` 已有 `batch_load_to_cpu`（ThreadPool），但 warmup 没用它
3. **预物化**：提前把所有 expert 从 safetensors 抽到 `.bin` 文件再跑实验
