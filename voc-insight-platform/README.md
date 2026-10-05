# VOC Lens 用户反馈洞察原型

面向反馈分散、逐条归纳不便的场景，提供 CSV 导入、清洗去重、反馈归类、主题汇总、关注优先级查看和简报导出。每个主题保留代表性原文，方便人工核验。

## 本地运行

```bash
python server.py
```

打开 http://127.0.0.1:8765 。需要 Python 3.10 或以上版本，无需第三方依赖或 API Key。

## 使用流程

1. 加载内置样例，或上传带表头的 CSV。
2. 选择文本列；日期、评分和渠道为可选字段。
3. 查看反馈总览、主题汇总和关注优先级。
4. 打开主题，核验代表性反馈。
5. 导出分析 CSV 或 Markdown 洞察简报。

## 数据和边界

`data/sample_feedback.csv` 包含 40 条编写的样例反馈，另有 18 条情感演示标注，均不代表真实用户数据。

原型使用词典情感判断、TF-IDF 与聚类，再归并为业务主题。关注优先级综合反馈量、负向率和严重度，权重为可调的规则假设。反讽、隐含语义和新领域词可能误判，真实应用需要独立人工标注和评审。

详细规则、验收条件和已知问题见 [产品说明](docs/product_spec.md)；实现结构见 [架构说明](docs/architecture.md)。

## 测试

```bash
python -m unittest discover -s tests -v
```

## 参考

参考 [customer_feedback_analyzer](https://github.com/asif-visionary/customer_feedback_analyzer) 的反馈整理流程、[Multi-Agent-Customer-Support](https://github.com/ANI-IN/Multi-Agent-Customer-Support) 的原文核验思路及 [TalentMatch-AI](https://github.com/Hossein-Mirzaei/TalentMatch-AI) 的轻量应用展示方式。参考不表示参与这些项目。

代码采用 MIT License。
