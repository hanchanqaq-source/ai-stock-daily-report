# 历史数据归档与清理规则

本功能提供轻量的历史数据归档摘要能力，用于把 `data/history/` 中的公开市场历史数据提炼为月度摘要，并生成清理候选清单。

## 能力边界

- 生成月度 Markdown 摘要，便于人工阅读。
- 生成月度 JSON 摘要，便于趋势分析、周报、月报、网页工作台和任务组分析复用。
- 生成月度 CSV 板块强弱频次摘要。
- 生成待删除候选清单。
- 默认不删除重要文件；后续真正清理必须显式确认。

## 输入与输出

优先读取：

- `data/history/market_history.csv`
- `data/history/market_snapshot_YYYY-MM-DD.json`

输出到：

- `data/archive_summaries/monthly_summary_YYYY-MM.md`
- `data/archive_summaries/monthly_summary_YYYY-MM.json`
- `data/archive_summaries/monthly_sector_stats_YYYY-MM.csv`
- `data/archive_summaries/delete_candidates_YYYY-MM-DD.md`
- `data/archive_summaries/cleanup_manifest.json`

扫描候选目录包括 `data/reports/`、`output/`、`logs/`、`cache/`、`tmp/`。目录不存在时会跳过并记录日志。

## 命令行用法

```bash
python scripts/archive_history.py --month YYYY-MM
python scripts/archive_history.py --latest-month
python scripts/archive_history.py --generate-delete-candidates
```

以上命令默认只生成摘要或候选清单，不会删除重要文件。清理候选清单会提示后续 cleanup 需要显式设置 `confirm_cleanup=true`。

## 隐私与安全

归档摘要只保存公开市场统计、行业/概念强弱频次、数据覆盖率统计、文件大小统计和非敏感文件路径。摘要不会保存 webhook、API Key、Token、用户金额、成本价、账户资产或个人身份信息。
