# 实验踩坑记录

> 本文件记录 MECC 端到端实验中的常见问题和解决方案。
> 每次遇到新坑追加一条，不覆盖旧条目。

---

## 1. 环境与硬件

### 1.1 K_H=4 OOM 在 A100 上（torch 2.5.1+cu121）

**现象**：`HBM_budget=50`（K_H=4）时构建成功（~67GB），但推理时 `batch_prefetch` 阶段 OOM。

**原因**：torch 2.5.1+cu121 比之前版本多占用 ~2GB 推理内存。

**解决**：降到 HBM=30（K_H=2）。原始代码同样 OOM（`git stash` 复现确认），非代码 bug。

### 1.2 `expandable_segments:True` 不一定有帮助

**结论**：不加更好。默认 PyTorch 内存分配器在这个场景下表现不错。

### 1.3 WikiText-2 联网失败

无外网环境 `datasets.load_dataset("wikitext")` 报错，自动回退到内置 prompts，不影响实验。

---

## 2. 多进程冲突

### 2.1 同一时间只能跑一个实验

两个 `run_e2e.py` 同时运行 → GPU 各占 ~33GB → 都 OOM 或死锁。

### 2.2 杀进程后确认干净再跑新实验

```bash
kill <pid> 2>/dev/null; sleep 2
ps aux | grep run_e2e | grep -v grep || echo "CLEAN"
```

---

## 3. 性能陷阱

### 3.1 batch_prefetch 不能随意限制

加了 `cpu_uids = cpu_uids[:max(0, gpu_avail)]` 想防 OOM，结果 `gpu_avail=0` → 所有 CPU expert 改成同步单读 → **100× 变慢**。

**教训**：先在纸上算峰值内存再动手改。

### 3.2 冷 SSD 是真实瓶颈，不是 bug

Mixtral 0.04 tok/s——每个 SSD miss 读 1GB，300MB/s → 3.3s。快速迭代用 `--warm_ssd` 或极小参数。

### 3.3 PyTorch 输出缓冲

`nohup` 后看不到输出 → 加 `PYTHONUNBUFFERED=1` 或 `python3 -u`。

---

## 4. 编译参数

### 4.1 `--uniform` vs per_layer_adaptive

默认随机 `per_layer_alpha` → 水塘分配比统一分配多 ~20% HBM slots。与之前 A100 实验对齐用 `--uniform`。

### 4.2 store_root 复用

store 可以复用跳过物化；换 HBM 预算时建议换 store。

---

## 5. 优化尝试与失败记录

### 5.1 M1 async_ssd_read（-27%，rejected）

ThreadPool 异步 SSD 读，期望 overlap。DeepSeek 0.83 vs 基线 1.14 tok/s。ThreadPool 开销 > 收益（专家小，~50ms 读完）。

### 5.2 M5 batch_prefetch_plus（-20%，rejected）

解码时每层 forward 结尾发起下一 token 的 SSD 预取。DeepSeek 0.96 vs M2 基线 1.20 tok/s。top_k=6 预测命中率低，I/O 来不及完成。

---

## 6. 数值异常

### 6.1 SwapMoE PPL=91 异常（DeepSeek）

DeepSeek L1 中 SwapMoE PPL=91，OURS/fiddler ~44。未排查，临时只看 tok/s 和命中率。

---

## 7. 提速方案

### 日常开发

```bash
# 极简参数（5-10 分钟）
--prompt_len 16 --max_new_tokens 4 --n_prompts 2 --skip_ppl --policies ours
# warm SSD（利用页缓存，快 10-100×，仅调试）
--warm_ssd
```

### 正式实验

```bash
# L1 DeepSeek（快，~25min 4 策略）
--hbm_budget 8 --cpu_budget 12 --alpha 0.73
# L2 Mixtral（慢，K_H=2 约 2h 2 策略）
--hbm_budget 30 --cpu_budget 40 --uniform
```
