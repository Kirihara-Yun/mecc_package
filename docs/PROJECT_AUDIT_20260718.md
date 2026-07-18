# MECC 项目接管基线审计（2026-07-18）

> 本文记录接管时点的可验证事实。它不是性能结论，也不替代
> `PROVENANCE.md`；后续事实变化时追加记录，不静默覆盖历史。

## 1. 审计范围

- 工作区、最近提交和未跟踪文件；
- Python / PyTorch / CUDA 可见性、内存和磁盘；
- 三条受保护 import 链；
- `verify_claims.py` 已登记 claim；
- L0 端到端 smoke；
- 最新 Mixtral K_H=2 实验与当前权威 Mixtral 基线的口径差异；
- THEORY 注册表与实现锚点。

本次未运行 L1/L2：当前受管执行会话无法访问 GPU 设备节点，且当前文件系统
仅余约 7GB，不能安全物化约 90GB 的 Mixtral expert store。

## 2. 环境事实

| 项目 | 审计结果 | 解释 |
|------|----------|------|
| 物理 GPU | A100 PCIe 80GB | PCI 枚举可见 `GA100 [A100 PCIe 80GB]`，NVIDIA 内核模块已加载 |
| 当前会话 GPU | 不可访问 | `/dev/nvidia*` 未透传，`nvidia-smi` 无法通信，`torch.cuda.is_available()==False` |
| PyTorch | 2.5.1+cu121 | 安装正常，但本会话不能创建 CUDA context |
| 系统内存 | 约 1TiB，总可用约 967GiB | 容量足够；这不代表当前会话可执行 GPU L2 |
| 文件系统 | 约 7GB 可用 | 不足以新建 Mixtral SSD store |

结论必须写成“物理机有 GPU，但当前执行会话不可访问”，不能写成“机器无 GPU”。

## 3. 工作区与链路

- 分支：`master`。
- 接管时存在 5 个未跟踪文件，均视为用户文件，不修改、不删除。
- `check_env.py` 的三条 import 链全部通过：
  - `e2e -> compiler.py`；
  - `runtime_spec -> compiler.py`；
  - `concurrent_tiered_cache -> real_tiered_cache`。
- `verify_claims.py`：29 OK、7 WARN、0 FAIL。
  - 已登记的 verified claim 均与对应 JSON 字段一致；
  - 两个较新的 Mixtral JSON 缺 `platform` / `run_time`；
  - DeepSeek 论文表 3 仍无匹配 JSON；
  - 1.33x 综合口径与 1.62x TPOT 口径必须区分。

## 4. L0 结果

命令：

```bash
cd mecc_package/e2e
python3 run_e2e.py --smoke --n_prompts 4 \
  --store_root /tmp/mecc_store_audit \
  --out /tmp/mecc_smoke_audit.json
```

结果：退出码 0；`ours/swapmoe/fiddler/naive` 四策略均完成；所有 exact 策略均报告
`exact(lossless)`；每个策略均触发 SSD 路径。

该结果只证明逻辑链路通过。随机 gate、微型 CPU 模型的 tok/s 和 speedup 不能作为性能证据。

## 5. 新旧 Mixtral 结果的审计判断

当前权威基线仍是 `results/raw/mixtral_real.json`（K_H=4、prompt_len=64）：
其 1.33x 已登记为 D2 verified。

2026-06-22 至 2026-06-24 新增了 K_H=2、prompt_len=32 的 L2 文件。它们显示出一致趋势：
OURS 的 CPU 命中率约 38%--40%，SSD 访问约 16%--18%；SwapMoE 的 CPU 命中约 12%，
SSD 访问约 43%--48%。这些是真机结果中的有价值证据，但目前不能直接替换 1.33x 主基线，原因是：

1. 预算与 prompt_len 不同，属于新的实验配置；
2. 两个最新文件缺强制元数据；
3. `run_e2e.py` 先将吞吐舍入到小数点后两位，再计算 speedup；0.04/0.02 因而机械地产生 2.0x，
   精度不足以支撑该加速比；
4. PPL 字段是 `exact(lossless)` 标记，而不是与旧主表同口径的数值 PPL。

因此，当前诚实口径是：K_H=2 新实验支持“联合动态 CPU tier 明显降低 SSD 访问”的趋势；
其精确端到端加速比需要保存未舍入测量值后重新计算并登记。

## 6. 理论状态

THEORY 注册表当前状态合理地区分了证据强度：

- `TH-001/002/003/007/008`：proven；
- `TH-004/005`：partial；
- `TH-006`：conjecture。

尤其需要保持以下克制：

- `compiler.py:optimize` 当前实现的是容量贪心填满，不是完整的边际平衡优化器；
- `estimate_alpha` 已改为给定观测排序后的有界离散 Zipf MLE；有限样本的排序选择偏差仍未消除；
- 联合 LRU 对动态 HBM + 静态 CPU 的普遍包含性尚未证明。

这些缺口不否定系统实验，但限制论文中可使用的理论措辞。

## 7. 下一步

1. 已修复评测输出：基于保留 6 位的吞吐计算 speedup；
2. 已让新 JSON 自动写入 `platform` 与带时区 `run_time`；
3. 已为上述行为增加 CPU 可运行测试；
4. 已修复 `estimate_alpha` 未使用访问计数的问题，并通过合成分布测试；
5. 在 GPU 设备透传和磁盘空间满足后，再复现 L2，不从旧舍入值反推新结论。

## 8. 后续执行记录（2026-07-18）

- 计划 1--4 已完成验证：新增与相关回归测试共 7 项通过；三条受保护 import
  链通过；L0 四策略 smoke 通过；`verify_claims.py` 为 30 OK、7 个已登记 WARN、
  0 FAIL；`git diff --check` 通过。
- L0 输出确认吞吐保留 6 位，并包含 `platform=CPU` 与带时区 `run_time`。记录见
  `mecc_package/results/logs/20260718_L0_smoke_metrics-provenance.md`。L0 吞吐不作为
  性能证据。
- GPU 透传与 `/data/qinzy` 空间恢复后，完成了 1 prompt、2 tokens、四策略的最小
  L2 预检；该预检仅验证真实 Mixtral 四策略路径，因样本极小且跳过数值 PPL，
  不用于刷新论文结论。
- 用户随后明确决定不再执行正式 L2 复现。因此计划 5 以“预检完成、正式复现取消”
  收口；当前权威 L2 结论仍仅引用 `results/raw/mixtral_real.json`，不从历史舍入值或
  本次最小预检反推新结论。
