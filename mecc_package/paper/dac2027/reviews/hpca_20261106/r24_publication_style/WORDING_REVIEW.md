# R15：直接描述缓存操作与等待时间

正文、章节标题、图注和实际嵌入的配图统一采用直接表述。

- victim / GPU victim → evicted expert、GPU LRU expert 或 expert evicted from HBM，按句子选择。
- joint victim retention → retention after GPU eviction。
- Retaining Victims across the Tier Boundary → Retaining Evicted Experts on the Host。
- inference critical path → Each selected expert executes once its weights are available in HBM.
- 图 2(e) → Retain evicted experts。
- 图 10(b) → Exposed time。
- weights survive on the host → weights remain on the host。

保持四段引言结构；数值、数据身份说明、参考文献及图 11 的三模型配色不变。旧版本不覆盖。逐项替换见 TERM_REPLACEMENTS.json。
