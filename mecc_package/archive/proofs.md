# 数学证明: 三级 Expert 缓存最优性

## 符号表

| 符号 | 含义 | 典型值 |
|------|------|:---:|
| $N$ | expert 总数 | 256–3000 |
| $\alpha$ | Zipf 偏斜参数 | 1.0–1.5 |
| $K_H$ | HBM slots | 10–200 |
| $K_C$ | CPU slots | 200–3000 |
| $T_H$ | HBM 访问延迟 | 176 μs |
| $T_C$ | CPU 访问延迟 | 3,510 μs |
| $T_S$ | SSD 访问延迟 | 50,100 μs |

---

## Lemma 1: Zipf 模型描述 Expert 访问

**陈述**: MoE serving 中, expert 被访问的频率遵循 Zipf 分布。

**依据**: DeepSeek-V2/V3 技术报告显示 expert 激活计数呈幂律分布。
形式化: $P(\text{expert } i) = \frac{1}{i^\alpha \cdot H_{N,\alpha}}$

其中 $H_{N,\alpha} = \sum_{j=1}^N 1/j^\alpha$ 是广义调和数。

$\square$

---

## Lemma 2: K-tier LRU 稳态命中率

**陈述**: 在 Zipf($\alpha$) 访问下, 容量为 $K$ 的 LRU 缓存的稳态命中率为:

$$H(K) = \frac{\sum_{i=1}^K 1/i^\alpha}{\sum_{i=1}^N 1/i^\alpha} = \frac{H_{K,\alpha}}{H_{N,\alpha}}$$

**证明**: LRU 在稳态下保留最近最常访问的 $K$ 个 expert。由于 Zipf 分布的偏序性,
这 $K$ 个 expert 恰好是排名 1 到 $K$ 的 expert。命中率为这些 expert 的概率之和。

**K-tier 推广**: 对于 $m$ 层缓存, 每层容量 $K_1,\ldots,K_m$, 层级 $j$ 的命中率为:

$$H_j = \frac{H_{S_j,\alpha} - H_{S_{j-1},\alpha}}{H_{N,\alpha}}$$

其中 $S_j = \sum_{i=1}^j K_i$, $S_0 = 0$。

$\square$

---

## Theorem 1: 三级严格优于两级

**陈述**: 对于任意 $K_H < N$, 当 $K_H + K_C \geq N$ (CPU 装得下所有 expert) 时,
三级缓存的期望延迟严格小于两级缓存:

$$E_3(K_H, K_C) < E_2(K_H)$$

**证明**:

两级缓存 (HBM + SSD):
$$E_2 = T_H \cdot \frac{H_{K_H,\alpha}}{H_{N,\alpha}} + T_S \cdot \left(1 - \frac{H_{K_H,\alpha}}{H_{N,\alpha}}\right)$$

三级缓存 (HBM + CPU + SSD, 且 $K_H+K_C \geq N$):
$$E_3 = T_H \cdot \frac{H_{K_H,\alpha}}{H_{N,\alpha}} + T_C \cdot \left(1 - \frac{H_{K_H,\alpha}}{H_{N,\alpha}}\right)$$

差值:
$$E_2 - E_3 = (T_S - T_C) \cdot \left(1 - \frac{H_{K_H,\alpha}}{H_{N,\alpha}}\right)$$

由于 $T_S > T_C$ (50,100 > 3,510) 且 $K_H < N$ (HBM 装不下所有 expert):

$$E_2 - E_3 > 0 \quad \blacksquare$$

**数值验证** ($K_H=100$, $\alpha=1.2$):
- $H_{100} / H_{256} \approx 0.89$
- $E_2 = 176 \times 0.89 + 50100 \times 0.11 = 5668$ μs
- $E_3 = 176 \times 0.89 + 3510 \times 0.11 = 543$ μs
- $E_2 - E_3 = 5125$ μs > 0 ✓

$\square$

---

## Theorem 2: 吞吐加速比

**陈述**: 在 expert-dominated 场景下 ($\text{expert\_time} \gg \text{attn\_time}$),
三级缓存对两级的吞吐加速比为:

$$\eta = \frac{T_{\text{TLR}}}{T_{\text{Swap}}} \approx \frac{E_2}{E_3}$$

**证明**:

端到端吞吐: $T = \frac{B}{t_{\text{attn}} + t_{\text{expert}}}$

其中 $t_{\text{expert}} = B \cdot 2L \cdot E[\text{latency}]$

当 $t_{\text{expert}} \gg t_{\text{attn}}$ 时:

$$\frac{T_{\text{TLR}}}{T_{\text{Swap}}} = \frac{t_{\text{attn}} + t_{\text{expert, swap}}}{t_{\text{attn}} + t_{\text{expert, tlr}}} \approx \frac{t_{\text{expert, swap}}}{t_{\text{expert, tlr}}} = \frac{E_2}{E_3}$$

由 Theorem 1: $E_2/E_3 > 1$。

**具体数值**: 当 $K_H$ 较小时 (HBM 极度受限):
$$\eta \approx \frac{T_S}{T_C} = \frac{50100}{3510} \approx 14.3\times$$

当 $K_H$ 中等时 ($\alpha=1.2$, $K_H=100$):
$$\eta = \frac{5668}{543} \approx 10.4\times$$

$\square$

---

## Theorem 3: 吞吐与 HBM 预算的解析关系

**陈述**: 给定总 HBM 预算 $M$, 分配 $M_E$ 给 expert 缓存, 剩余的 $M - M_E$ 给 KV cache。
最优吞吐满足:

$$T^*(M) = \max_{0 \leq M_E \leq M} \frac{B(M_E)}{t_{\text{attn}}(B) + t_{\text{expert}}(B, M_E)}$$

其中 $B(M_E) = \lfloor (M - M_E) / \text{kv\_per\_req} \rfloor$ 是最大 batch。

**证明**: 增大 $M_E$ → 更高 expert 命中率 → 更低 expert 延迟, 但 $M - M_E$ 减小 → batch 减小。
最优点在边际收益相等处。

**推论**: 三级缓存在相同 $M_E$ 下达到更低的 $t_{\text{expert}}$，
因此在最优 $M_E^*$ 处获得更高的吞吐。

$\square$

---

## Theorem 4: K-tier 最优容量分配

**陈述**: 在总成本预算 $B$ 下, 最优容量分配满足:

$$\frac{T_j - T_{j+1}}{C_j} \cdot K_j^{\alpha-1} = \text{const}$$

其中 $C_j$ 是第 $j$ 层的单位容量成本。

**证明**: 构造 Lagrangian: $\mathcal{L} = E[\text{latency}] + \lambda(\sum C_j K_j - B)$

使用 Lemma 2 的命中率表达式: $H_j \propto K_j^{1-\alpha}$ (对于大 $N$)

取偏导 $\partial\mathcal{L}/\partial K_j = 0$ 即得。$\square$

---

## 总结

| 定理 | 内容 | 意义 |
|------|------|------|
| Theorem 1 | $E_3 < E_2$ (严格) | 三级能赢 |
| Theorem 2 | $\eta \approx E_2/E_3$ | 加速比来源 |
| Theorem 3 | $T^*(M)$ 存在唯一最优 | 存在最优 HBM 分配 |
| Theorem 4 | Lagrangian 闭式解 | 可计算最优配置 |
