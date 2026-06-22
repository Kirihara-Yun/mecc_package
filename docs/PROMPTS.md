# 提示词库 —— 人类用 MECC 仓库的各种情景

> 这是**给人类准备的提示词手册**：当你想让 AI 助手（或自己）在本仓库做某件事时，
> 复制对应情景的提示词、替换 `<尖括号>` 占位，即可直接用。
> 所有提示词都假设 AI 会先读 [`AGENTS.md`](../AGENTS.md) 与 [`APPLICABILITY.md`](./APPLICABILITY.md)。

---

## 0. 万能开场（建议每次新会话第一句）

```
你正在协作一个 MoE expert 三级缓存编译器科研项目（MECC）。
请先读 AGENTS.md 和 docs/APPLICABILITY.md，理解：方法只在「模型连 CPU 都装不下、被迫落 SSD」时才有效。
然后再回答我下面的问题，所有结论都要和这两份文档的叙事保持一致。
```

---

## 1. 理解项目 / 入门

**情景：第一次接触，想快速搞懂这是什么**
```
用三段话向我解释 MECC：(1) 它解决什么问题；(2) 它的方法核心（编译期放置 + 运行期三级 LRU）；
(3) 它在什么条件下才有效、什么条件下没用。最后告诉我该读哪几个文件深入。
```

**情景：想理解代码架构**
```
基于 docs/ARCHITECTURE.md 和 mecc_package/mecc_framework/，
画出从「gate 选中 expert」到「计算完成」的数据流，并说明 HBM/CPU/SSD 三级 miss 时各发生什么。
```

**情景：搞不清两套实现的区别**
```
mecc_framework/ 和 e2e/ 都实现了三级缓存，它们的定位有什么不同？我做实验出论文主表该用哪个？
```

---

## 2. 判断适用性（最常见、最重要）

**情景：我有个新模型，想知道 MECC 对它有没有用**
```
我打算在 <模型名，如 Qwen2-57B-A14B> 上用 MECC，目标机器 GPU 显存 <X>GB、CPU 内存 <Y>GB。
请按 docs/APPLICABILITY.md 的决策树判断：MECC 对这个模型+这台机器是否有效？给出 expert 总量估算和结论。
```

**情景：审稿人/同事质疑「为什么不用 DeepSeek 当主结果」**
```
帮我准备一段回应：解释为什么 DeepSeek-V2-Lite 只是对照场景而非主战场，
为什么 Mixtral（连 CPU 都装不下、落 SSD）才是 MECC 真正成立的证据。引用真实数据。
```

---

## 3. 跑实验 / 复现

**情景：本机快速验证逻辑（不下载模型）**
```
带我跑通 e2e 的 smoke 自检，解释每一步在验证什么，以及为什么 smoke 不体现加速。
```

**情景：在真机上复现 Mixtral 主表**
```
我有一台 <RTX 5090 32GB / A100 80GB>、CPU 内存 <Y>GB、NVMe 盘 <Z>GB 空闲。
请按 mecc_package/e2e/README_E2E.md 给我一份从下载 Mixtral 到产出 main_table 的完整命令清单，
并标注每个参数（hbm_budget/cpu_budget/alpha/cold_ssd）该怎么填、为什么。
```

**情景：跑 α profiling**
```
解释 scripts/profile_*.py 各自 profile 什么，给我在 <模型> 上跑 profiling 并把结果喂给编译器的完整流程。
```

---

## 4. 扩展新模型 / 新功能

**情景：接入一个新的 MoE 架构**
```
我想让 MECC 支持 <模型架构，如 Qwen-MoE>。请基于 mecc_framework/models/ 的 ModelAdapter 模式，
告诉我需要新增/修改哪些文件、expert 权重命名怎么解析、forward gate 模式选哪种。先给方案再动手。
```

**情景：加一个新缓存策略对比**
```
我想新增一个 baseline 策略 <名字>，机制是 <描述>。请说明在 mecc_framework/cache/engine.py
（或 e2e/policy_plugin.py）里怎么加，保证它和现有四策略 apples-to-apples（同预算同 store 同 prompt）。
```

---

## 5. 调参

**情景：命中率不理想 / 想优化吞吐**
```
我在 <模型> 上跑出来 SSD 命中率高达 <X>%、吞吐只有 <Y> tok/s。
请结合 docs/GLOSSARY.md 的 K_H/K_C/alpha 含义和 tuning_log.md 的经验，给我调参建议。
```

**情景：预算怎么分配**
```
我的卡是 <显存>GB、CPU <内存>GB。请帮我估算 hbm_budget / cpu_budget 该留多少给 expert
（要扣掉 trunk+attn+KV cache），以及对应大概的 K_H/K_C。
```

---

## 6. 读结果 / 写论文

**情景：解读一个结果 JSON**
```
读 mecc_package/results/<文件>.json，用一张表告诉我四策略的 TTFT/TPOT/tokens·s/PPL/命中分布，
并指出 OURS 相对 SwapMoE 的加速来自哪里（结合 SSD 命中率变化）。
```

**情景：生成论文主表段落**
```
基于 results/raw/mixtral_real.json，写一段论文 Results 文字：强调「同精度（无损 PPL）下更快」，
给出 1.33× 加速与 SSD 命中从 34.5%→17.6% 的解释。口径要和 e2e/README_E2E.md 一致。
```

---

## 7. 排障

**情景：import 报错**
```
我改了文件后 e2e 跑不起来，报 <错误>。请先检查 AGENTS.md 第 3 节的硬约束
（compiler.py 位置、e2e 扁平 import、scripts 内部依赖）是否被破坏。
```

**情景：SSD 测出来超慢 / 怀疑没真正落盘**
```
我的 decode 极慢，怀疑 SSD 层有问题。帮我确认 store_root 是不是真 NVMe（不是 tmpfs）、
是否开了 cold_ssd、以及这是否属于「有意为之的真实瓶颈」。
```

---

## 8. 维护仓库

**情景：整理 / 重组文件**
```
请在不破坏 AGENTS.md 第 3 节硬约束的前提下，<整理需求>。
移动任何文件前先 grep 引用确认无断链，且不要删除 results/ 下任何实验数据。
```

**情景：更新文档保持一致**
```
我刚改了 <代码/结果>。请同步更新相关文档（README / ARCHITECTURE / APPLICABILITY / GLOSSARY），
确保所有「方法有效性/主场景/数字」措辞与 docs/APPLICABILITY.md 一致。
```

---

> 没覆盖到的情景？用第 0 节开场 + 自然语言描述需求即可。
> 关键原则：**让 AI 先读 AGENTS.md + APPLICABILITY.md，再保证结论与真实数据一致。**
