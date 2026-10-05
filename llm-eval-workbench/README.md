# ModelBench 大模型回答评测原型

导入已保存的回答，检查业务要点覆盖、数值一致性与格式，并汇总比较预设时延和成本。支持查看缺失要点、无依据数字及格式错误等 Bad Case。

## 本地运行

```bash
python server.py
```

打开 http://127.0.0.1:8766 。需要 Python 3.10 或以上版本，无需第三方依赖或 API Key。

## 使用流程

1. 加载内置样例或导入评测 CSV。
2. 查看各组回答的检查结果与通过率。
3. 比较质量、时延和成本的汇总视图。
4. 查看错误案例，核验参考材料和具体错误。

## 数据来源

样例包含 6 个场景、3 个匿名模拟模型，共 18 条模拟回答。`latency_ms` 和 `cost_usd` 都是预设演示值。

程序没有调用真实模型，没有采集真实响应时长、Token 用量或账单。平均时延、P95 时延及平均成本只是在模拟字段上计算的统计值。

## 方法与边界

关键词匹配、数字匹配和格式检查是确定性规则，适合解释单条失败原因，但不能完整衡量语义正确性。当前权重、门槛和三种对比策略用于展示取舍，不构成真实模型选型结论。

详细口径见 [评测说明](docs/evaluation_design.md)。参考 [Promptfoo](https://github.com/promptfoo/promptfoo) 和 [DeepEval](https://github.com/confident-ai/deepeval) 的测试集与断言思路。

## 测试

```bash
python -m unittest discover -s tests -v
```

代码采用 MIT License。
