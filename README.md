# AI 产品作品集

两个可本地运行的产品原型：VOC Lens 用户反馈洞察和 ModelBench 离线回答评测。项目展示反馈整理、原文核验、回答检查和多维对比流程。

| 项目 | 使用场景 | 演示数据 | 入口 |
| --- | --- | --- | --- |
| VOC Lens | 把分散反馈整理成主题，辅助判断关注优先级 | 40 条编写的样例反馈 | [项目说明](voc-insight-platform/README.md) |
| ModelBench | 查看回答要点、数值、格式和错误案例 | 6 个场景、3 个匿名模拟模型，共 18 条回答 | [项目说明](llm-eval-workbench/README.md) |

## 运行

需要 Python 3.10 或以上版本，无需 API Key。启动两个项目时使用两个终端。

```bash
cd voc-insight-platform
python server.py
```

浏览器打开 http://127.0.0.1:8765 。

```bash
cd llm-eval-workbench
python server.py
```

浏览器打开 http://127.0.0.1:8766 。Windows 也可以在对应目录运行 `run.ps1`，按 Ctrl+C 结束服务。

## 演示步骤

VOC Lens：加载样例，查看主题和关注优先级，打开代表性原文，导出分析明细与 Markdown 简报。

ModelBench：加载样例，比较回答检查结果，查看缺失要点、无依据数字和格式错误；时延和成本用于展示汇总对比。

## 数据与方法

两个项目均使用演示数据，没有真实用户量、商业转化或生产部署结果。VOC Lens 的优先级来自可调规则，需要人工复核，不能直接作为产品排期。

ModelBench 不调用真实模型。时延和成本由 CSV 预设字段提供，不是实测延迟，也不是依据真实 Token 用量和价格计算的费用。规则检查结果不能等同于完整语义质量评估。

## 测试

分别在项目目录运行：

```bash
python -m unittest discover -s tests -v
```

VOC Lens 包含 6 项测试，ModelBench 包含 7 项测试。GitHub Actions 配置会在 Windows 和 Linux 上运行两套测试。

## 开源参考

ModelBench 参考 [Promptfoo](https://github.com/promptfoo/promptfoo) 和 [DeepEval](https://github.com/confident-ai/deepeval) 的评测思路。VOC Lens 的参考来源见其项目说明。仓库采用 MIT License。
