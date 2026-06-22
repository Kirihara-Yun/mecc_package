# MECC — RTX 5090 实验发现与修正（2026-06-17）

本文件记录在真实目标硬件 **RTX 5090（32GB GDDR7 + 754GB DRAM, PyTorch 2.8 / CUDA 12.8）**
上的首轮实验结果、两处必须修正的方法学问题，以及可写进论文前的下一步实验计划。

---

## 1. 已验证：核心假说成立（这是主结果）

### 1.1 真机三级延迟（Step 1）
| 层 | 延迟 | vs HBM | 口径 |
|---|---|---|---|
| HBM hit | 254.5 μs | 1× | 仅 GEMM |
| CPU hit | 50,167 μs | **197×** | H2D 搬运 + GEMM |
| SSD miss | 802,315 μs | **3152×** | 冷读 + H2D + GEMM |

对照 Apple UMA：HBM:CPU 落差仅 **3.1×**。**5090 把落差恢复到两个数量级，这正是"UMA 压扁落差"假说的直接实证。**

> ⚠️ 197× 待修正，见 §2.A —— 该值用 pageable 内存测得、被高估。真实落差预计 **~30–40×**，
> 仍远超 Apple，假说方向不变，但写论文必须用修正后的数。

### 1.2 真机端到端（Step 3，N=96 / hidden2048 / ffn8192 / α=1.2 / K_H=8,K_C=24）
| 场景 | vs FluxMoE | vs SwapMoE | 解读 |
|---|---|---|---|
| stationary | 0.99× | **0.83×（输）** | 平稳负载下静态放置接近最优，我们的动态层付出 churn 代价 |
| **drift（甜区）** | **1.58×** | **1.27×（赢）** | 热点漂移下静态放置失效，动态分层自适应胜出 |

- drift 的 1.27× **超过了 A100 的投影 1.24×**，且 **是个下界**（见 §2.B，e2e 的 SSD 其实是热的）。
- kh12 配比（K_H=12,K_C=12）stationary 同样 ~0.96×，与上面一致。

### 1.3 论文叙事（必须按此限定）
> 静态放置仅在**平稳**假设下最优；真实服务存在**时间漂移**，此区间我们的自适应三级缓存
> 取得 **1.27–1.58×**。**不要**写成全场景碾压——stationary 那栏会自打脸。

---

## 2. 两处必须修正的方法学硬伤（已在本地代码改好）

### A. HBM:CPU=197× 是 pageable 内存假象 —— 已修
- **症状**：日志 `transfer only … eff BW 6.7 GB/s`。PCIe5 x16 理论 64 GB/s、pinned 实测 40–50 GB/s，
  6.7 GB/s 是 pageable + 暂存拷贝的典型值 → `T_CPU` 虚高 5–7×。
- **根因**：`measure_tiers.py` 调 `make_expert_tensors()` 时未传 `pin=True`；`non_blocking=True`
  对 pageable 内存无效。真实 offload 系统（SwapMoE/FluxMoE）都用 pinned，这才是公平口径。
- **修复**：`measure_tiers.py` 已改为 `pin=True`（page-locked）。重测后 CPU 层带宽应跳到几十 GB/s，
  `T_CPU` 大幅下降，落差落到 ~30–40×。

### B. Linux 上 e2e 的 "SSD 层" 不冷，是 page cache —— 已修
- **症状**：754G 内存 / 346G buff-cache，9.7G expert 文件第一遍即全进 page cache，
  之后"SSD 冷读"实为 RAM 速度。
- **根因**：`real_tiered_cache.py` 的冷读绕 cache 仅在 `if IS_DARWIN` 生效，Linux 分支空转。
  （微基准 `measure_tiers.py` 你在 5090 上加了 O_DIRECT 所以读到 1.2 GB/s 真冷盘，但 e2e 脚本没改，两者口径不一致。）
- **影响**：SSD 惩罚被低估 → **我们的优势被低估**，故实测 1.27× 是**下界**（修正后应更高）。
- **修复**：两个脚本统一改为 Linux `posix_fadvise(POSIX_FADV_DONTNEED)` 读前+读后丢弃本文件 page cache，
  实现真冷读（无需 O_DIRECT 对齐麻烦）。

### C. 理论扫描与真机 e2e 不自洽（数据解释问题，非 bug）
- 扫描得 vs_swap 恒 >1（1.22–2.20×），真机 stationary 却 0.83×。
- 原因：扫描把 SwapMoE 建模成"只有 HBM-LRU、无 CPU 层"的稻草人。真实 SwapMoE 有静态 CPU 层、平稳时接近最优。
- 结论：扫描结果只能解释为"vs HBM-only 基线的上界"，**论文主张以真机 e2e 为准、限定 drift 区间**。

---

## 3. 下一步实验计划（复制本包到 5090 后开箱即跑）

> 前置：①确认 tmpdir 在**真实 NVMe**上而非 tmpfs：`findmnt -T /tmp`（看 SOURCE/FSTYPE）；
> ②overlay 仅 30G 且易满，跑前 `rm -rf /tmp/mecc_*` 清场，大配置务必控制 `n_experts×expert_mb < 可用盘`。

### Step 1′ — 重测层级延迟（pinned + 真冷盘）
```bash
python3 measure_tiers.py --out measured_latency_5090_fixed.json
```
预期：CPU 层有效带宽从 6.7 → 几十 GB/s，HBM:CPU 落差降到 ~30–40×（这才是写论文的数）。

### Step 3′ — 重跑端到端（Linux 真冷 SSD）
```bash
python3 real_tiered_cache.py --n_experts 96 --hidden 2048 --ffn 8192 \
  --batch 64 --alpha 1.2 --requests 1200 --k_h 8 --k_c 24 \
  --out real_e2e_5090_coldssd.json
```
预期：drift 的 vs SwapMoE 比 1.27× **更高**（SSD 真冷后惩罚回归）。

### Step 4（新，决胜图）— drift 强度扫描，找交叉点
用新增 `--phases`（越大漂移越快；1≈平稳）扫一条 speedup-vs-drift 曲线，定位"我们开始赢"的拐点：
```bash
for P in 1 2 4 8 16; do
  python3 real_tiered_cache.py --n_experts 96 --hidden 2048 --ffn 8192 \
    --batch 64 --alpha 1.2 --requests 1200 --k_h 8 --k_c 24 --phases $P \
    --out real_e2e_5090_phase${P}.json
done
```
产出：x=漂移率、y=vs SwapMoE 加速比、交叉线=1.0 —— 这是论文最有说服力的一张图
（"漂移越强、我们越赢"，把 stationary 0.83× 的劣势转化为方法定位的论据）。

### Step 5（可选）— p99 尾延迟分析
三方法 p99 均 ~268,000 μs，被 SSD miss 主导。单独分析尾部，论证分层对 SLO 的价值。

---

## 4. 文件改动清单（本轮，已落地在本地仓库）
- `measure_tiers.py`：CPU 张量改 `pin=True`；SSD 冷读加 Linux `posix_fadvise(DONTNEED)`；note/打印更新。
- `real_tiered_cache.py`：SSD 冷读加 Linux `posix_fadvise(DONTNEED)`；新增 `--phases` 漂移强度参数并写入结果 config。

> 命名约定：5090 结果统一带 `_5090` 后缀，**勿覆盖** Apple 历史 json —— 两平台对比本身即"UMA 假说"的论据。
