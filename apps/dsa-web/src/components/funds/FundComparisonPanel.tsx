import { GitCompareArrows, Layers3, LoaderCircle } from 'lucide-react';
import { useState } from 'react';
import { fundDataApi, type FundComparisonReadonlyResponse } from '../../api/fundData';
import { Card, InlineAlert } from '../common';
import FundAnalysisSourceSelector, { type FundAnalysisSelection } from './FundAnalysisSourceSelector';

type FundComparisonPanelProps = {
  mode: 'compare' | 'industry-exposure';
  language: 'zh' | 'en';
};

const FundComparisonPanel = ({ mode, language }: FundComparisonPanelProps) => {
  const [selection, setSelection] = useState<FundAnalysisSelection>({ source: 'manual', codes: [] });
  const [approved, setApproved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<FundComparisonReadonlyResponse | null>(null);
  const codes = selection.codes;
  const minimum = mode === 'compare' ? 2 : 1;
  const validCodes = codes.length >= minimum
    && codes.length <= 4
    && codes.every((code) => /^\d{6}$/.test(code))
    && new Set(codes).size === codes.length;

  const run = async () => {
    if (!validCodes || !approved || loading) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await fundDataApi.compareAksharePublicFunds(codes);
      setResult(response);
      if (response.status !== 'completed-readonly') {
        setError(language === 'zh' ? '基金对比数据暂时不可用，请按错误状态重试。' : 'Fund comparison data is unavailable. Please retry later.');
      }
    } catch {
      setError(language === 'zh' ? '公开基金数据读取失败，未保存任何数据。' : 'Public fund lookup failed. No data was saved.');
    } finally {
      setLoading(false);
    }
  };

  const comparison = result?.comparison;
  const icon = mode === 'compare' ? <GitCompareArrows className="h-5 w-5 text-cyan" /> : <Layers3 className="h-5 w-5 text-cyan" />;

  return (
    <div className="space-y-4" data-testid={`fund-d2-${mode}`}>
      <InlineAlert
        variant="info"
        title={language === 'zh' ? 'Build D2：披露基金对比与行业穿透' : 'Build D2: disclosed comparison and industry exposure'}
        message={language === 'zh'
          ? '行业数据直接采用 AKShare 公布的基金行业配置；持仓重合仅按最新披露前十大计算。结果不是行业周期、生产力或买卖建议。'
          : 'Industry data comes directly from AKShare fund disclosures. Holding overlap uses only the latest disclosed top holdings. This is not cycle, productivity, or trading advice.'}
      />

      <Card padding="md">
        <div className="flex items-center gap-2">{icon}<h2 className="font-semibold text-foreground">{language === 'zh' ? (mode === 'compare' ? '选择并对比基金' : '选择并查看行业穿透') : (mode === 'compare' ? 'Choose and compare funds' : 'Choose and review industry exposure')}</h2></div>
        <p className="mt-2 text-xs leading-5 text-secondary-text">
          {language === 'zh'
            ? `可手动输入，或从当前用户的持仓、自选中选择 ${mode === 'compare' ? '2–4' : '1–4'} 只基金。每次读取都需要重新确认。`
            : `Enter codes manually or choose ${mode === 'compare' ? '2–4' : '1–4'} funds from the active user’s holdings or watchlist. Every lookup requires approval.`}
        </p>
        <FundAnalysisSourceSelector
          language={language}
          minimum={minimum}
          maximum={4}
          inputLabel={language === 'zh' ? '基金代码' : 'Fund codes'}
          placeholder={mode === 'compare' ? '例如 000001, 110022' : '例如 000001'}
          onSelectionChange={(nextSelection) => {
            setSelection(nextSelection);
            setResult(null);
            setError('');
          }}
        />
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            className="btn-primary flex min-w-40 items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!validCodes || !approved || loading}
            onClick={run}
          >
            {loading && <LoaderCircle className="h-4 w-4 animate-spin" />}
            {loading ? (language === 'zh' ? '读取中' : 'Loading') : (language === 'zh' ? '读取并计算' : 'Read and calculate')}
          </button>
        </div>
        <label className="mt-3 flex items-start gap-2 text-xs leading-5 text-secondary-text">
          <input type="checkbox" className="mt-1" checked={approved} onChange={(event) => setApproved(event.target.checked)} />
          <span>{language === 'zh' ? '我确认本次只读取公开基金披露并在内存中计算，不读取账户、不交易、不通知、不调用 AI、不保存。' : 'I approve this public disclosure lookup and in-memory calculation only: no account access, trading, notifications, AI, or persistence.'}</span>
        </label>
        {!validCodes && codes.length > 0 && (
          <p className="mt-2 text-xs text-amber-300">{language === 'zh' ? `需要 ${minimum}–4 个不重复的六位基金代码。` : `Enter ${minimum}–4 unique six-digit fund codes.`}</p>
        )}
        {error && <p className="mt-3 text-sm text-red-400" role="alert">{error}</p>}
      </Card>

      {comparison && (
        <div className="space-y-4" data-testid="fund-comparison-result">
          <Card padding="md">
            <div className="flex flex-wrap gap-2 text-xs text-secondary-text">
              <span className="rounded-full border border-border px-3 py-1">{result?.providerLabel}</span>
              <span>{language === 'zh' ? '读取时间' : 'Fetched'}：{comparison.source.fetched_at}</span>
              <span>{language === 'zh' ? '状态' : 'Status'}：{comparison.data_status}</span>
            </div>
            {comparison.reason && <p className="mt-3 text-xs leading-5 text-amber-300">{comparison.reason}</p>}
          </Card>

          {comparison.funds.map((fund) => (
            <Card key={fund.code} padding="md">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="font-semibold text-foreground">{fund.bundle.profile?.name ?? fund.code} <span className="text-xs font-normal text-secondary-text">{fund.code}</span></h2>
                <span className="text-xs text-secondary-text">{fund.data_status}</span>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                <div className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{language === 'zh' ? '类型' : 'Type'}</p><p className="mt-1 text-sm text-foreground">{fund.bundle.profile?.fund_type ?? '缺失'}</p></div>
                <div className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{language === 'zh' ? '单位净值' : 'Unit NAV'}</p><p className="mt-1 text-sm text-foreground">{fund.bundle.nav?.unit_nav ?? '缺失'}</p></div>
                <div className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{language === 'zh' ? '净值日期' : 'NAV date'}</p><p className="mt-1 text-sm text-foreground">{fund.bundle.nav?.nav_date ?? '缺失'}</p></div>
                <div className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{language === 'zh' ? '前十大集中度' : 'Top holdings concentration'}</p><p className="mt-1 text-sm text-foreground">{fund.top10_holdings_concentration_pct ? `${fund.top10_holdings_concentration_pct}%` : '缺失'}</p></div>
                <div className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{language === 'zh' ? '前三行业集中度' : 'Top 3 industry concentration'}</p><p className="mt-1 text-sm text-foreground">{fund.industry_exposure ? `${fund.industry_exposure.top3_concentration_pct}%` : '缺失'}</p></div>
              </div>

              {fund.industry_exposure && (
                <div className="mt-5">
                  <h3 className="text-sm font-semibold text-foreground">{language === 'zh' ? '披露行业配置' : 'Disclosed industry allocation'} · {fund.industry_exposure.report_date}</h3>
                  <p className="mt-1 text-xs text-secondary-text">{language === 'zh' ? '已披露行业合计' : 'Disclosed industry total'}：{fund.industry_exposure.disclosed_total_pct}%</p>
                  <div className="mt-2 overflow-x-auto">
                    <table className="w-full min-w-96 text-left text-xs">
                      <thead className="text-secondary-text"><tr><th className="py-2">{language === 'zh' ? '行业' : 'Industry'}</th><th>{language === 'zh' ? '占净值比例' : 'NAV weight'}</th><th>{language === 'zh' ? '市值（万元）' : 'Value (CNY 10k)'}</th></tr></thead>
                      <tbody>{fund.industry_exposure.industries.map((item) => <tr key={item.industry_name} className="border-t border-border"><td className="py-2 text-foreground">{item.industry_name}</td><td className="text-foreground">{item.weight_pct}%</td><td className="text-secondary-text">{item.market_value_cny_10k ?? '缺失'}</td></tr>)}</tbody>
                    </table>
                  </div>
                </div>
              )}

              {fund.bundle.holdings && (
                <div className="mt-5">
                  <h3 className="text-sm font-semibold text-foreground">{language === 'zh' ? '最新披露前十大持仓' : 'Latest disclosed top holdings'} · {fund.bundle.holdings.report_period}</h3>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-secondary-text">
                    {fund.bundle.holdings.positions.map((item) => <span key={item.security_code} className="rounded-full border border-border px-3 py-1">{item.security_name} {item.weight_pct}%</span>)}
                  </div>
                </div>
              )}
              {(fund.missing_sections.length > 0 || fund.warnings.length > 0) && <p className="mt-4 text-xs leading-5 text-amber-300">{[...fund.missing_sections.map((item) => `${language === 'zh' ? '缺失' : 'Missing'}: ${item}`), ...fund.warnings].join('；')}</p>}
            </Card>
          ))}

          {mode === 'compare' && comparison.pair_overlaps.map((overlap) => (
            <Card key={`${overlap.left_code}-${overlap.right_code}`} padding="md">
              <h2 className="font-semibold text-foreground">{overlap.left_code} ↔ {overlap.right_code}</h2>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{language === 'zh' ? '披露前十大持仓重合下限' : 'Disclosed holdings overlap floor'}</p><p className="mt-1 text-lg font-semibold text-foreground">{overlap.disclosed_holdings_overlap_pct}%</p><p className="mt-1 text-xs text-secondary-text">{overlap.common_holdings.map((item) => item.security_name).join('、') || (language === 'zh' ? '无共同披露持仓' : 'No common disclosed holdings')}</p></div>
                <div className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{language === 'zh' ? '披露行业重合' : 'Disclosed industry overlap'}</p><p className="mt-1 text-lg font-semibold text-foreground">{overlap.disclosed_industry_overlap_pct}%</p><p className="mt-1 text-xs text-secondary-text">{overlap.common_industries.map((item) => item.industry_name).join('、') || (language === 'zh' ? '无共同披露行业' : 'No common disclosed industries')}</p></div>
              </div>
              <p className="mt-3 text-xs leading-5 text-amber-300">{overlap.warnings.join('；')}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default FundComparisonPanel;
