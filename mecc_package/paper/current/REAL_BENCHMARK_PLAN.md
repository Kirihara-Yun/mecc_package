# Insight 消融：模型与输入数据执行清单

当前幻灯片第 7–9 页的横轴是被测 **MoE 模型**：Mixtral-8×7B、
Qwen2-57B-A14B、Mixtral-8×22B。每一组柱子是三种缓存/放置方案。
WikiText-2 等名称是生成提示词的**数据集**，并非模型或对照方案。
后两个模型尚未接入并完成端到端测试，图中柱高仍是理想目标。

模型来源：[Mixtral-8×7B](https://huggingface.co/mistralai/Mixtral-8x7B-Instruct-v0.1)、
[Qwen2-57B-A14B](https://huggingface.co/Qwen/Qwen2-57B-A14B-Instruct)、
[Mixtral-8×22B](https://huggingface.co/mistralai/Mixtral-8x22B-Instruct-v0.1)。

## 数据集与图中标签

| 图中标签 | 公开数据集 | 用途 | 来源 |
|---|---|---|---|
| WikiText-2 | `Salesforce/wikitext`, `wikitext-2-raw-v1` | 通用文本续写 | https://huggingface.co/datasets/Salesforce/wikitext |
| C4 | English C4 | 网页文本续写 | https://www.tensorflow.org/datasets/catalog/c4 |
| GSM8K | `openai/gsm8k`, `main` | 数学问答提示词 | https://huggingface.co/datasets/openai/gsm8k |
| MBPP | Google Research MBPP | Python 代码生成提示词 | https://github.com/google-research/google-research/blob/master/mbpp/README.md |

这些名字指公开、可下载的数据集，**不代表 MECC 已在其上跑出结果**。当前
`run_e2e.py` 只自动尝试 WikiText-2；其余三个数据集需要新增固定 prompt manifest
读取入口。`results/raw/mixtral_real.json` 没保存每个 prompt 的数据集身份和 ID，
不能把它的聚合 TPOT 当作三个模型的独立测量。

## 固定实验口径

1. 对横轴每个模型分别固定模型和 tokenizer revision。每个输入数据集冻结版本、
   split、样本 ID、prompt 模板和 tokenized 输入哈希。画像和评测使用不重叠样本。
2. 每个策略使用同一份 fp16 expert store、相同实际 HBM/CPU 字节上限、相同 SSD
   冷读设置、相同生成长度和确定性解码。每个 prompt 做成配对试验，并保存逐请求
   TTFT、TPOT、SSD demand miss/字节、H2D/D2H 字节与峰值内存。
3. Insight I：只改变初始放置规则（平均分配 / 全局排序 / 逐层画像），运行期规则固定。
   先接通各模型的真实 per-layer 路由计数；当前端到端入口不会自动收集该画像。
4. Insight II：初始放置固定，只改变 CPU 固定 / 独立更新 / 联合更新的缓存规则。
5. Insight III：三个模型均使用同一个 WikiText-2→GSM8K 切换协议。
   报告切换后等长窗口，并保留稳定负载作为对照。
6. 每组先做能运行完的 pilot，再冻结正式样本数和重复方案。正式图只使用原始日志
   归约的结果；不能用设计目标柱高补缺，也不能为没有重复的实验添加误差线。

相关脚本：`../build_insight_pairs.py`；当前设计目标数据：
`../dac2027/ideal_assumptions.json`。正式出图前，按 `docs/EXPERIMENTS.md`
记录实验，再按 `docs/PROVENANCE.md` 登记来源并运行 `verify_claims.py`。
