# D1 受控缓存回放记录

日期：2026-10-27 初次运行，2026-10-28 修订汇报。平台/精确 UTC 运行时间、脚本 SHA、git commit、trace 哈希均见原始 JSON；实验不是 GPU 推理。

命令：`python mecc_package/scripts/motivation_causal_replay.py`。

协议：`docs/HPCA_CAUSAL_REPLAY_PROTOCOL.md`。v1 保留；v2 使用同生成机制的独立训练、添加独立 LRU 与全局 LRU 参考。N=16、H=2、C=4、8 个配对种子、每条测试 1024 请求；无预算外镜像、预取或计时模型。全部 192 条 v2 结果保留。

成功判据：脚本退出码 0；每请求 H/C 容量断言通过；训练/测试 RNG 分离；阶段内 shuffle 直方图相同；联合排他驻留断言与全局 LRU 的逐请求 SSD miss 断言通过。

结果与精确值：`raw/motivation_causal_replay_20261027_v2.json:summaries`。主要观察：画像联合臂与随机联合臂长期接近，画像静态臂在人工漂移后可能变差；访问次序、动态保留与跨层重复共同影响 miss。SSD miss 更少不等于硬件更快，联合臂 D2H 对象数另存，不能忽略迁移成本。

禁止结论：本实验不证明实际 Mixtral 有相同局部性，不证明 CUDA 正确性，不给 A100 tok/s，不证明新替换算法，也不证明稿件达到 HPCA 接收水平。
