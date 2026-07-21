import { Activity, Factory, LoaderCircle, TrendingUp } from 'lucide-react';
import { useState } from 'react';
import { fundDataApi, type FundIndustryCycleReadonlyResponse } from '../../api/fundData';
import { Card, InlineAlert } from '../common';
import FundAnalysisSourceSelector, { type FundAnalysisSelection } from './FundAnalysisSourceSelector';

type Props = {
  language: 'zh' | 'en';
};

const PHASE_LABELS = {
  zh: {
    recovery: '复苏', expansion: '扩张', overheated: '过热', slowdown: '放缓', contraction: '收缩', insufficient: '证据不足',
  },
  en: {
    recovery: 'Recovery', expansion: 'Expansion', overheated: 'Overheated', slowdown: 'Slowdown', contraction: 'Contraction', insufficient: 'Insufficient evidence',
  },
} as const;

const PRODUCTIVITY_LABELS = {
  zh: { improving: '改善', stable: '稳定', weakening: '走弱', insufficient: '证据不足' },
  en: { improving: 'Improving', stable: 'Stable', weakening: 'Weakening', insufficient: 'Insufficient evidence' },
} as const;

function metric(value: string | null, suffix = '%'): string {
  return value === null ? '缺失' : `${value}${suffix}`;
}

const FundIndustryCyclePanel = ({ language }: Props) => {
  const [selection, setSelection] = useState<FundAnalysisSelection>({ source: 'manual', codes: [] });
  const [approved, setApproved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [response, setResponse] = useState<FundIndustryCycleReadonlyResponse | null>(null);
  const codes = selection.codes;
  const validCodes = codes.length >= 1
    && codes.length <= 4
    && codes.every((code) => /^\d{6}$/.test(code))
    && new Set(codes).size === codes.length;

  const run = async () => {
    if (!validCodes || !approved || loading) return;
    setLoading(true);
    setError('');
    setResponse(null);
    try {
      const result = await fundDataApi.fetchAkshareFundIndustryCycle(codes);
      setResponse(result);
      if (result.status !== 'completed-readonly') {
        setError(language === 'zh' ? '行业周期证据暂时不可用，请按错误状态稍后重试。' : 'Industry-cycle evidence is unavailable. Please retry later.');
      }
    } catch {
      setError(language === 'zh' ? '公开证据读取失败，未保存任何结果。' : 'Public evidence lookup failed. Nothing was saved.');
    } finally {
      setLoading(false);
    }
  };

  const cycle = response?.cycle;

  return (
    <div className="space-y-4" data-testid="fund-d3-industry-cycle">
      <InlineAlert
        variant="info"
        title={language === 'zh' ? 'Build D3：行业周期与经营生产力代理证据' : 'Build D3: industry-cycle and operating-productivity proxy evidence'}
        message={language === 'zh'
          ? '短期周期和长期经营证据分开计算；生产力仅为营收、利润、ROE、经营现金流等代理，不等同于全要素生产率，也不会生成买卖或调仓建议。'
          : 'Short-cycle and longer-horizon operating evidence are separate. Productivity uses revenue, profit, ROE, and cash-flow proxies only; it is not total-factor productivity or trading advice.'}
      />

      <Card padding="md">
        <div className="flex items-center gap-2"><TrendingUp className="h-5 w-5 text-cyan" /><h2 className="font-semibold text-foreground">{language === 'zh' ? '读取基金行业周期证据' : 'Read fund industry-cycle evidence'}</h2></div>
        <p className="mt-2 text-xs leading-5 text-secondary-text">
          {language === 'zh' ? '从手动输入、当前用户持仓或当前用户自选中选择 1–4 只基金。最多分析合计权重最高的 6 个可核验行业，每次读取都需要重新确认。' : 'Choose 1–4 funds from manual input, active-user holdings, or the active-user watchlist. Up to six verifiable industries by aggregate weight are analyzed, with approval required each time.'}
        </p>
        <FundAnalysisSourceSelector
          language={language}
          minimum={1}
          maximum={4}
          inputLabel={language === 'zh' ? '基金代码' : 'Fund codes'}
          placeholder="例如 000001, 110022"
          onSelectionChange={(nextSelection) => {
            setSelection(nextSelection);
            setResponse(null);
            setError('');
          }}
        />
        <div className="mt-4 flex justify-end">
          <button type="button" className="btn-primary flex min-w-40 items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50" disabled={!validCodes || !approved || loading} onClick={run}>
            {loading && <LoaderCircle className="h-4 w-4 animate-spin" />}
            {loading ? (language === 'zh' ? '读取中' : 'Loading') : (language === 'zh' ? '读取周期证据' : 'Read cycle evidence')}
          </button>
        </div>
        <label className="mt-3 flex items-start gap-2 text-xs leading-5 text-secondary-text">
          <input type="checkbox" className="mt-1" checked={approved} onChange={(event) => setApproved(event.target.checked)} />
          <span>{language === 'zh' ? '我确认本次仅读取公开基金、行业行情和业绩报表，在内存中计算；不读取账户、不交易、不通知、不调用 AI、不保存。' : 'I approve this public fund, industry market, and financial report lookup for in-memory calculation only: no accounts, trading, notifications, AI, or persistence.'}</span>
        </label>
        {!validCodes && codes.length > 0 && <p className="mt-2 text-xs text-amber-300">{language === 'zh' ? '需要 1–4 个不重复的六位基金代码。' : 'Enter 1–4 unique six-digit fund codes.'}</p>}
        {error && <p className="mt-3 text-sm text-red-400" role="alert">{error}</p>}
      </Card>

      {cycle && (
        <div className="space-y-4" data-testid="fund-industry-cycle-result">
          <Card padding="md">
            <div className="flex flex-wrap gap-2 text-xs text-secondary-text">
              <span className="rounded-full border border-border px-3 py-1">{response?.providerLabel}</span>
              <span>{language === 'zh' ? '读取时间' : 'Fetched'}：{cycle.fetched_at}</span>
              <span>{language === 'zh' ? '基准' : 'Benchmark'}：{cycle.benchmark_code}</span>
              <span>{language === 'zh' ? '业绩报告期' : 'Financial period'}：{cycle.financial_report_period ?? '缺失'}</span>
            </div>
            {[...cycle.missing_evidence, ...cycle.warnings].length > 0 && <p className="mt-3 text-xs leading-5 text-amber-300">{[...cycle.missing_evidence.map((item) => `缺失: ${item}`), ...cycle.warnings].join('；')}</p>}
          </Card>

          {cycle.funds.map((fund) => (
            <Card key={fund.code} padding="md">
              <h2 className="font-semibold text-foreground">{fund.name ?? fund.code} <span className="text-xs font-normal text-secondary-text">{fund.code}</span></h2>
              <p className="mt-1 text-xs text-secondary-text">{language === 'zh' ? '持仓报告期' : 'Holdings period'}：{fund.holdings_report_period ?? '缺失'} · {language === 'zh' ? '本次分析披露权重' : 'Analyzed disclosed weight'}：{fund.analyzed_weight_pct}%</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {fund.industry_links.map((item) => <span key={item.industry_name} className="rounded-full border border-border px-3 py-1 text-xs text-foreground">{item.industry_name} {item.fund_weight_pct}%</span>)}
                {fund.industry_links.length === 0 && <span className="text-xs text-amber-300">{language === 'zh' ? '没有可核验的行业连接' : 'No verifiable industry link'}</span>}
              </div>
              {(fund.unclassified_holdings.length > 0 || fund.omitted_industries > 0) && <p className="mt-3 text-xs text-amber-300">{language === 'zh' ? `未分类持仓 ${fund.unclassified_holdings.length} 项；因上限省略行业 ${fund.omitted_industries} 项。` : `${fund.unclassified_holdings.length} holdings unclassified; ${fund.omitted_industries} industries omitted by limit.`}</p>}
            </Card>
          ))}

          {cycle.industries.map((industry) => (
            <Card key={industry.industry_name} padding="md">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div><h2 className="font-semibold text-foreground">{industry.industry_name}</h2><p className="mt-1 text-xs text-secondary-text">{industry.board_code} · {industry.metrics.as_of_date ?? '日期缺失'}</p></div>
                <div className="flex gap-2 text-xs"><span className="rounded-full border border-cyan/40 px-3 py-1 text-cyan">{language === 'zh' ? '周期' : 'Cycle'}：{PHASE_LABELS[language][industry.phase]}</span><span className="rounded-full border border-border px-3 py-1 text-secondary-text">{language === 'zh' ? '置信度' : 'Confidence'}：{industry.confidence}</span></div>
              </div>
              <p className="mt-2 text-xs text-secondary-text">{language === 'zh' ? '来源接口' : 'Source interfaces'}：{industry.source_interfaces.join(' · ')}</p>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                {[
                  [language === 'zh' ? '20日趋势' : '20d trend', metric(industry.metrics.return_20d_pct)],
                  [language === 'zh' ? '60日趋势' : '60d trend', metric(industry.metrics.return_60d_pct)],
                  [language === 'zh' ? '成交额变化' : 'Turnover change', metric(industry.metrics.turnover_change_20d_pct)],
                  [language === 'zh' ? '上涨股票比例' : 'Rising breadth', metric(industry.metrics.breadth_rise_ratio_pct)],
                  [language === 'zh' ? '相对沪深300' : 'Vs CSI 300', metric(industry.metrics.relative_strength_20d_pct)],
                ].map(([label, value]) => <div key={label} className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{label}</p><p className="mt-1 text-sm font-semibold text-foreground">{value}</p></div>)}
              </div>

              <div className="mt-4 rounded-lg border border-border p-4">
                <div className="flex items-center gap-2"><Factory className="h-4 w-4 text-cyan" /><h3 className="text-sm font-semibold text-foreground">{language === 'zh' ? '经营生产力代理证据' : 'Operating-productivity proxy evidence'}：{PRODUCTIVITY_LABELS[language][industry.productivity.status]}</h3></div>
                <p className="mt-2 text-xs text-secondary-text">{industry.productivity.report_period ?? '报告期缺失'} · {language === 'zh' ? '覆盖成份股' : 'Covered constituents'} {industry.productivity.covered_constituents}/{industry.productivity.total_constituents} · {language === 'zh' ? '置信度' : 'Confidence'} {industry.productivity.confidence}</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5 text-xs">
                  <span>{language === 'zh' ? '营收同比中位数' : 'Revenue YoY median'}：{metric(industry.productivity.revenue_yoy_median_pct)}</span>
                  <span>{language === 'zh' ? '利润同比中位数' : 'Profit YoY median'}：{metric(industry.productivity.profit_yoy_median_pct)}</span>
                  <span>ROE：{metric(industry.productivity.roe_median_pct)}</span>
                  <span>{language === 'zh' ? '毛利率中位数' : 'Gross margin median'}：{metric(industry.productivity.gross_margin_median_pct)}</span>
                  <span>{language === 'zh' ? '经营现金流为正比例' : 'Positive operating cash flow'}：{metric(industry.productivity.operating_cashflow_positive_ratio_pct)}</span>
                </div>
              </div>

              {(industry.missing_evidence.length > 0 || industry.productivity.missing_dimensions.length > 0) && <div className="mt-4 flex items-start gap-2 text-xs leading-5 text-amber-300"><Activity className="mt-0.5 h-4 w-4 shrink-0" /><span>{language === 'zh' ? '缺失证据' : 'Missing evidence'}：{[...industry.missing_evidence, ...industry.productivity.missing_dimensions].join('、')}</span></div>}
            </Card>
          ))}

          {cycle.industries.length === 0 && <Card padding="md"><p className="text-sm text-amber-300">{language === 'zh' ? '当前没有足够的可核验行业证据，不生成周期阶段。' : 'No verifiable industry evidence is sufficient to produce a cycle stage.'}</p></Card>}
        </div>
      )}
    </div>
  );
};

export default FundIndustryCyclePanel;
