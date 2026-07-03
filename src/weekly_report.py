# -*- coding: utf-8 -*-
"""Weekly market review report built from persisted daily market snapshots."""
from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Optional

logger = logging.getLogger(__name__)

INSUFFICIENT_HISTORY_MESSAGE = "历史样本不足，已开始记录，后续周报将自动形成趋势复盘。"
DATA_MISSING = "数据暂缺"


@dataclass(frozen=True)
class WeeklyReportResult:
    report: str
    discord_summary: str
    filename: str
    loaded_snapshots: int
    insufficient_history: bool
    week_start: date
    week_end: date


def resolve_week_range(today: Optional[date] = None) -> tuple[date, date]:
    current = today or date.today()
    if current.weekday() >= 5:
        current = current - timedelta(days=current.weekday() - 4)
    start = current - timedelta(days=current.weekday())
    return start, min(start + timedelta(days=4), current)


def load_week_snapshots(
    history_dir: str | Path = "data/history",
    *,
    today: Optional[date] = None,
) -> tuple[list[dict[str, Any]], date, date]:
    week_start, week_end = resolve_week_range(today)
    root = Path(history_dir)
    snapshots: list[dict[str, Any]] = []
    current = week_start
    while current <= week_end:
        path = root / f"market_snapshot_{current.isoformat()}.json"
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("[WEEKLY] skip damaged snapshot path=%s error=%s", path, exc)
                current += timedelta(days=1)
                continue
            if isinstance(payload, dict):
                item = dict(payload)
                item.setdefault("date", current.isoformat())
                snapshots.append(item)
        current += timedelta(days=1)
    logger.info("[WEEKLY] loaded_snapshots=%s", len(snapshots))
    logger.info("[WEEKLY] week_start=%s", week_start.isoformat())
    logger.info("[WEEKLY] week_end=%s", week_end.isoformat())
    return snapshots, week_start, week_end


def generate_weekly_report(
    history_dir: str | Path = "data/history",
    *,
    today: Optional[date] = None,
) -> WeeklyReportResult:
    snapshots, week_start, week_end = load_week_snapshots(history_dir, today=today)
    insufficient = len(snapshots) < 2
    logger.info("[WEEKLY] insufficient_history=%s", str(insufficient).lower())
    filename = f"AI股票基金每周复盘报告_{week_start.strftime('%Y')}-W{week_start.isocalendar().week:02d}.md"
    metrics = [_normalize_snapshot(s) for s in snapshots]
    report = _render_full_report(metrics, week_start, week_end, insufficient)
    summary = _render_discord_summary(metrics, insufficient)
    logger.info("[WEEKLY] report_generated=true")
    return WeeklyReportResult(report, summary, filename, len(snapshots), insufficient, week_start, week_end)


def save_weekly_report(result: WeeklyReportResult, reports_dir: str | Path = "reports") -> str:
    root = Path(reports_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / result.filename
    path.write_text(result.report, encoding="utf-8")
    return str(path)


def run_weekly_report(*, notifier: Any = None, send_notification: bool = True, history_dir: str | Path = "data/history") -> WeeklyReportResult:
    logger.info("[REPORT] type=weekly")
    result = generate_weekly_report(history_dir)
    save_weekly_report(result)
    status = "skipped"
    if send_notification and notifier is not None:
        try:
            status = "success" if notifier.send_to_discord(result.discord_summary) else "failed"
        except Exception as exc:  # pragma: no cover
            status = "failed"
            logger.warning("Discord weekly report send failed: %s", exc)
    logger.info("[DISCORD] weekly_send_status=%s", status)
    return result


def _normalize_snapshot(raw: Mapping[str, Any]) -> dict[str, Any]:
    ml = _mapping(raw.get("market_light") or raw.get("market_light_snapshot") or raw)
    breadth = _mapping(raw.get("breadth") or raw.get("market_breadth") or ml.get("breadth"))
    return {
        "date": str(raw.get("date") or raw.get("trade_date") or ml.get("trade_date") or ""),
        "signal": _num(raw.get("market_signal") or raw.get("signal") or ml.get("score")),
        "up_ratio": _num(raw.get("up_ratio") or raw.get("advance_ratio") or breadth.get("up_ratio") or breadth.get("advance_ratio")),
        "turnover": _num(raw.get("turnover") or raw.get("amount") or raw.get("成交额") or ml.get("turnover")),
        "limit_diff": _num(raw.get("limit_diff") or raw.get("limit_up_down_diff") or ml.get("limit_diff")),
        "indices": _mapping(raw.get("indices") or raw.get("global_indices") or ml.get("indices")),
        "strong": _sector_items(raw.get("strong_sectors") or raw.get("leading_sectors") or raw.get("top_industries")),
        "weak": _sector_items(raw.get("weak_sectors") or raw.get("lagging_sectors") or raw.get("bottom_industries")),
    }


def _render_full_report(items: list[dict[str, Any]], week_start: date, week_end: date, insufficient: bool) -> str:
    lines = ["# 📊 AI股票基金每周复盘报告", "", "## 本周结论", _conclusion(items, insufficient), ""]
    if insufficient:
        lines += [INSUFFICIENT_HISTORY_MESSAGE, ""]
    lines += ["## 1. 本周核心数据", *_core_lines(items), "", "## 2. 本周指数表现", *_index_lines(items), "", "## 3. 本周盘面对比", _snapshot_table(items), "", "## 4. 本周趋势判断", *_trend_lines(items), "", "## 5. 本周主线板块", *_sector_lines(items), "", "## 6. 本周风险雷达", *_risk_lines(items), "", "## 7. 下周观察重点", *_watch_lines(items), "", "## 8. 操作建议", *_advice_lines(items), ""]
    return "\n".join(lines)


def _render_discord_summary(items: list[dict[str, Any]], insufficient: bool) -> str:
    return "\n".join(["# 📊 AI股票基金每周复盘报告", "", "## 本周结论", _conclusion(items, insufficient), "", "## 1. 本周核心数据", *_core_lines(items, compact=True), "", "## 2. 本周趋势", f"• 市场宽度：{_width_judgement(items)}", f"• 成交额：{_turnover_judgement(items)}", f"• 指数承接：{_index_judgement(items)}", f"• 短线情绪：{_emotion_judgement(items)}", "", "## 3. 本周强弱方向", *_sector_summary(items), "", "## 4. 下周观察", *_watch_lines(items)[:3], "", "---", "完整周报请查看 artifact 附件。", "", "运行信息：", "- 报告类型：weekly", "- 生成状态：success"])


def _core_lines(items, compact=False):
    if not items: return [f"• 本周交易日数：0 天", f"• {INSUFFICIENT_HISTORY_MESSAGE}"]
    first, last = items[0], items[-1]
    avg_up = _avg([x["up_ratio"] for x in items]); avg_turn = _avg([x["turnover"] for x in items]); avg_diff = _avg([x["limit_diff"] for x in items])
    return [f"• {'交易日数' if compact else '本周交易日数'}：{len(items)} 天", f"• 盘面信号：{_fmt(first['signal'],0)}/100 → {_fmt(last['signal'],0)}/100，变化 {_signed(_diff(first['signal'], last['signal']),0)} 分", f"• 平均上涨占比：{_fmt(avg_up,1)}%", f"• 平均成交额：{_fmt(avg_turn,0)} 亿", f"• 平均涨跌停差：{_signed(avg_diff,0)}", f"• 本周状态：{_market_state(items)}"]

# helpers
_mapping=lambda v: v if isinstance(v, Mapping) else {}
def _num(v):
    if v is None: return None
    if isinstance(v, str): v=re.sub(r"[^0-9.+-]", "", v)
    try: return float(v)
    except (TypeError, ValueError): return None
def _avg(vals):
    nums=[v for v in vals if isinstance(v,(int,float))]
    return mean(nums) if nums else None
def _fmt(v,d=1): return DATA_MISSING if v is None else f"{v:.{d}f}"
def _signed(v,d=1): return DATA_MISSING if v is None else f"{v:+.{d}f}"
def _diff(a,b): return None if a is None or b is None else b-a
def _pp(a,b): return _diff(a,b)
def _sector_items(v):
    if not isinstance(v, list): return []
    out=[]
    for x in v:
        if isinstance(x, str): out.append((x, None))
        elif isinstance(x, Mapping): out.append((str(x.get("name") or x.get("sector") or x.get("industry") or ""), _num(x.get("change_pct") or x.get("pct") or x.get("涨幅"))))
    return [(n,p) for n,p in out if n]
def _market_state(items):
    avg=_avg([x['up_ratio'] for x in items]); sig=items[-1]['signal'] if items else None
    if avg is None and sig is None: return DATA_MISSING
    score = sig if sig is not None else avg
    return "偏强" if score >= 60 else "震荡" if score >= 45 else "偏弱防守"
def _conclusion(items, insufficient):
    if insufficient: return INSUFFICIENT_HISTORY_MESSAGE
    return f"本周市场状态为{_market_state(items)}，市场宽度{_width_judgement(items)}，成交额{_turnover_judgement(items)}，下周仍需观察指数承接和主线持续性。"
def _snapshot_table(items):
    rows=["| 日期 | 盘面信号 | 上涨占比 | 成交额 | 涨跌停差 | 状态 |","| --- | --- | --- | --- | --- | --- |"]
    for x in items: rows.append(f"| {x['date'] or DATA_MISSING} | {_fmt(x['signal'],0)}/100 | {_fmt(x['up_ratio'],1)}% | {_fmt(x['turnover'],0)}亿 | {_signed(x['limit_diff'],0)} | {_market_state([x])} |")
    return "\n".join(rows) if items else DATA_MISSING
def _trend_lines(items):
    if len(items)<2: return [INSUFFICIENT_HISTORY_MESSAGE]
    f,l=items[0],items[-1]
    return [f"• 市场宽度：本周上涨占比从 {_fmt(f['up_ratio'],1)}% 变化到 {_fmt(l['up_ratio'],1)}%，变化 {_signed(_pp(f['up_ratio'],l['up_ratio']),1)} 个百分点。判断：{_width_judgement(items)}。", f"• 成交额：本周成交额从 {_fmt(f['turnover'],0)} 亿变化到 {_fmt(l['turnover'],0)} 亿。判断：{_turnover_judgement(items)}。", f"• 涨跌停差：本周涨跌停差从 {_signed(f['limit_diff'],0)} 变化到 {_signed(l['limit_diff'],0)}。判断：{_emotion_judgement(items)}。", f"• 指数承接：本周主要指数平均涨跌幅为 {DATA_MISSING}。判断：{_index_judgement(items)}。"]
def _width_judgement(items):
    if len(items)<2: return DATA_MISSING
    d=_diff(items[0]['up_ratio'],items[-1]['up_ratio'])
    return DATA_MISSING if d is None else ("改善" if d>5 else "转弱" if d<-5 else "变化不大")
def _turnover_judgement(items):
    if len(items)<2: return DATA_MISSING
    d=_diff(items[0]['turnover'],items[-1]['turnover'])
    return DATA_MISSING if d is None else ("放大" if d>500 else "缩小" if d<-500 else "变化不大")
def _emotion_judgement(items):
    if len(items)<2: return DATA_MISSING
    d=_diff(items[0]['limit_diff'],items[-1]['limit_diff'])
    return DATA_MISSING if d is None else ("短线情绪改善" if d>10 else "降温" if d<-10 else "局部活跃")
def _index_judgement(items): return DATA_MISSING
def _index_lines(items): return ["🇨🇳 A股", f"• 上证指数：{DATA_MISSING}", f"• 深证成指：{DATA_MISSING}", f"• 创业板指：{DATA_MISSING}", "🇭🇰 港股", DATA_MISSING, "🇺🇸 美股", DATA_MISSING, "🇯🇵 日股", DATA_MISSING, "🇰🇷 韩股", DATA_MISSING]
def _sector_counts(items, key):
    c=Counter(); pct=defaultdict(list)
    for x in items:
        for n,p in x[key]: c[n]+=1; (pct[n].append(p) if p is not None else None)
    return [(n,c[n],_avg(pct[n])) for n,_ in c.most_common(5)]
def _sector_lines(items):
    if len(items)<2: return ["历史样本不足，暂不生成完整周度板块统计。"]
    lines=["📈 本周强势方向 Top 5"] + [f"{i}. {n}：出现 {cnt} 次，周内平均涨幅 {_fmt(avg,2)}%" for i,(n,cnt,avg) in enumerate(_sector_counts(items,'strong'),1)]
    lines += ["", "📉 本周弱势方向 Top 5"] + [f"{i}. {n}：出现 {cnt} 次，周内平均跌幅 {_fmt(avg,2)}%" for i,(n,cnt,avg) in enumerate(_sector_counts(items,'weak'),1)]
    return lines if len(lines)>3 else ["历史样本不足，暂不生成完整周度板块统计。"]
def _sector_summary(items):
    strong=[f"{i}. {n}" for i,(n,_,_) in enumerate(_sector_counts(items,'strong')[:3],1)] or [DATA_MISSING]
    weak=[f"{i}. {n}" for i,(n,_,_) in enumerate(_sector_counts(items,'weak')[:3],1)] or [DATA_MISSING]
    return ["📈 强势方向：", *strong, "", "📉 弱势方向：", *weak]
def _risk_lines(items): return [f"• 指数风险：中", f"• 成交额风险：{_turnover_judgement(items)}", f"• 市场宽度：{_width_judgement(items)}", "• 题材持续性：一般", f"• 综合风险：{'高' if _market_state(items).startswith('偏弱') else '中'}"]
def _watch_lines(items): return ["• 观察主要指数能否修复承接。", "• 观察成交额是否继续放大。", "• 观察本周强势板块是否延续。", "• 观察上涨占比能否回到 50% 以上。", "• 观察涨跌停差是否继续保持正值。"]
def _advice_lines(items): return ["• 如果市场宽度继续低于 45%，优先控制仓位。", "• 如果成交额放大但指数继续下跌，避免追高弱反弹。", "• 如果强势方向连续 2～3 天延续，可重点观察主线持续性。", "• 周报只作趋势参考，不构成投资建议。"]
