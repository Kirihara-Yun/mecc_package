# MECC 端到端调参日志

## 硬件环境
- GPU: NVIDIA A100 80GB（空闲 ~79GB）
- 内存: 1TB
- 系统盘: /dev/sda (ext4, 879GB)
- 数据盘: /dev/sdb (/data, 3.5TB)

---

## 实验 1：DeepSeek-V2-Lite，HBM=40GB / CPU=50GB

| 参数 | 值 |
|------|-----|
| 模型 | deepseek-ai/DeepSeek-V2-Lite（30GB, 26层×64 experts, 16.5MB/expert）|
| 编译 | K_H=64 / K_C=0 / SSD=0（全部落GPU） |
| 预测命中 | HBM=100% |

| Policy | TTFT | TPOT | tok/s |
|--------|------|------|-------|
| ours | 207ms | 67ms | 14.53 |
| swapmoe | 209ms | 67ms | 14.41 |
| fiddler | 207ms | 67ms | 14.40 |
| naive | 208ms | 68ms | 14.35 |

> ❌ **失败**：A100 显存太大，全部 expert 落 GPU，三级缓存未触发，四策略无差异。

---

## 实验 2：DeepSeek-V2-Lite，HBM=3GB / CPU=10GB（模拟受限显存）

| 参数 | 值 |
|------|-----|
| 编译 | K_H=**7** / K_C=23 / SSD=34 |
| SSD 读取 | **515 GB**（20× 模型大小） |

> ❌ **失败**：K_H 太小（7个），top-6 routing 导致每 token 都从 SSD 大量搬 expert，缓存颠簸严重。

---

## 实验 3：DeepSeek-V2-Lite，HBM=8GB / CPU=12GB ✅ 有效

| 参数 | 值 |
|------|-----|
| 编译 | K_H=**19** / K_C=28 / SSD=17 |
| 预测命中 | HBM=61.9% / CPU=27.2% / SSD=10.9% |

| Policy | TTFT | TPOT | tok/s | HBM命中 | CPU命中 | SSD命中 |
|--------|------|------|-------|---------|---------|---------|
| **ours** | **7.49s** | 995ms | **0.92** | 72.2% | **5.5%** | 22.3% |
| swapmoe | 11.37s | 961ms | 0.92 | 69.1% | **0.0%** | 30.9% |
| fiddler | 8.12s | 1351ms | 0.70 | 66.3% | **0.0%** | 33.7% |
| naive | ❌ 未完成 | | | | | |

关键发现：
- **OURS TTFT 快 1.52×** vs swapmoe
- **OURS 是唯一有效利用 CPU 缓存的策略**（5.5% vs 对手 0%）
- swapmoe/fiddler 静态放置完全失效（CPU 命中 = 0%）
- PPL 一致 = 44.752，验证无损

---

## 实验 4：Mixtral-8x7B，HBM=45GB / CPU=30GB

| 参数 | 值 |
|------|-----|
| 模型 | Mixtral-8x7B-Instruct（~90GB, 32层×8 experts, 336MB/expert）|
| 编译 | K_H=**4** / K_C=2 / SSD=2 |
| SSD 读取 | **514 GB** → 未完成 |

> ❌ **失败**：336MB/expert 太重，即使 10% SSD 命中率也导致巨量 I/O。Mixtral expert 太大，不适合做三级缓存 benchmark。

---

## 总结

| 发现 | 内容 |
|------|------|
| 有效配置 | DeepSeek-V2-Lite + HBM=8 / CPU=12 → K_H=19, K_C=28, SSD=17 |
| 核心优势 | OURS 动态 LRU 使 CPU tier 有效命中（5.5%），对手静态放置 = 0% |
| 适用模型 | expert 小（~16MB）、数量多（64+），如 DeepSeek 系列 |
| 不适用模型 | expert 大（>300MB），如 Mixtral，SSD 搬运代价过高 |
| A100 局限 | 80GB 对 ~30GB 模型太充裕，需手动限制 HBM 触发三级缓存 |
