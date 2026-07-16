import { Layers3, LoaderCircle, Scale, ShieldAlert, Waves } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  fundDataApi,
  type FundPortfolioAdvicePosition,
  type FundPortfolioAdviceReadonlyResponse,
  type FundRiskDimensionStatus,
  type FundRiskProfile,
} from '../../api/fundData';
import { usePortfolioUsers } from '../../contexts/PortfolioUserContext';
import { Card, InlineAlert } from '../common';

type Props = { language: 'zh' | 'en' };

const STATUS_LABELS = {
  zh: { normal: '未触发关注', watch: '需要关注', high: '优先复核', insufficient: '证据不足', 'not-applicable': '不适用' },
  en: { normal: 'No threshold', watch: 'Review', high: 'Priority review', insufficient: 'Insufficient', 'not-applicable': 'Not applicable' },
} as const;

const PROFILE_LABELS = {
  zh: { conservative: '稳健', balanced: '均衡', aggressive: '进取' },
  en: { conservative: 'Conservative', balanced: 'Balanced', aggressive: 'Aggressive' },
} as const;

function normalizePositions(
  holdings: readonly { code: string; amount: number; targetAllocation?: number }[],
): { positions: FundPortfolioAdvicePosition[]; error: string } {
  const grouped = new Map<string, { amount: number; target: number | null; targetComplete: boolean }>();
  for (const holding of holdings) {
    const code = holding.code.trim();
    if (!/^\d{6}$/.test(code) || !Number.isFinite(holding.amount) || holding.amount <= 0) {
      return { positions: [], error: '基金代码必须为六位数字，持有金额必须大于 0。' };
    }
    const current = grouped.get(code) ?? { amount: 0, target: 0, targetComplete: true };
    current.amount += holding.amount;
    if (holding.targetAllocation == null || !Number.isFinite(holding.targetAllocation)) {
      current.targetComplete = false;
      current.target = null;
    } else if (current.targetComplete) {
      current.target = (current.target ?? 0) + holding.targetAllocation;
    }
    grouped.set(code, current);
  }
  if (grouped.size === 0) return { positions: [], error: '当前用户还没有可分析的基金持仓。' };
  if (grouped.size > 4) return { positions: [], error: 'Build D4 每次最多分析 4 只不同基金，请先缩小当前持仓范围。' };
  const entries = [...grouped.entries()];
  const total = entries.reduce((sum, [, item]) => sum + item.amount, 0);
  let assigned = 0;
  const positions = entries.map(([code, item], index) => {
    const weightPct = index === entries.length - 1
      ? Number((100 - assigned).toFixed(6))
      : Number(((item.amount / total) * 100).toFixed(6));
    assigned += weightPct;
    return {
      code,
      weightPct,
      targetWeightPct: item.targetComplete ? item.target : null,
    };
  });
  return { positions, error: '' };
}

function StatusBadge({ status, language }: { status: FundRiskDimensionStatus; language: 'zh' | 'en' }) {
  const tone = status === 'high' ? 'border-red-400/40 text-red-300' : status === 'watch' ? 'border-amber-400/40 text-amber-300' : 'border-border text-secondary-text';
  return <span className={`rounded-full border px-3 py-1 text-xs ${tone}`}>{STATUS_LABELS[language][status]}</span>;
}

function value(valueText: string | null, suffix = '%') {
  return valueText == null ? '缺失' : `${valueText}${suffix}`;
}

const FundPortfolioAdvicePanel = ({ language }: Props) => {
  const { activeUser, activeUserId, activeFundHoldings } = usePortfolioUsers();
  const normalized = useMemo(() => normalizePositions(activeFundHoldings), [activeFundHoldings]);
  const portfolioKey = normalized.positions.map((item) => `${item.code}:${item.weightPct}:${item.targetWeightPct ?? '-'}`).join('|');
  const [riskProfile, setRiskProfile] = useState<FundRiskProfile>('balanced');
  const [approved, setApproved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [response, setResponse] = useState<FundPortfolioAdviceReadonlyResponse | null>(null);

  useEffect(() => {
    setRiskProfile('balanced');
    setApproved(false);
    setLoading(false);
    setError('');
    setResponse(null);
  }, [activeUserId, portfolioKey]);

  const run = async () => {
    if (normalized.error || !approved || loading) return;
    setLoading(true);
    setError('');
    setResponse(null);
    try {
      const result = await fundDataApi.fetchAkshareFundPortfolioAdvice(normalized.positions, riskProfile);
      setResponse(result);
      if (result.status !== 'completed-readonly') {
        setError(language === 'zh' ? '组合风险证据暂时不可用，请按错误状态稍后重试。' : 'Portfolio risk evidence is unavailable. Please retry later.');
      }
    } catch {
      setError(language === 'zh' ? '公开证据读取失败，未保存任何结果。' : 'Public evidence lookup failed. Nothing was saved.');
    } finally {
      setLoading(false);
    }
  };

  const advice = response?.advice;

  return (
    <div className="space-y-4" data-testid="fund-d4-portfolio-advice">
      <InlineAlert
        variant="info"
        title={language === 'zh' ? 'Build D4：当前用户基金组合风险与配置复核' : 'Build D4: active-user fund risk and allocation review'}
        message={language === 'zh'
          ? '只把基金代码和归一化占比送到本机只读接口；不发送用户名、金额、成本或账户。建议由固定规则生成，只用于人工复核，不自动交易。'
          : 'Only fund codes and normalized weights reach the local read-only API. User identity, amounts, costs, and accounts are not sent. Deterministic guidance is for manual review only.'}
      />

      <Card padding="md">
        <div className="flex items-center gap-2"><ShieldAlert className="h-5 w-5 text-cyan" /><h2 className="font-semibold text-foreground">{language === 'zh' ? `${activeUser.name} 的基金组合` : `${activeUser.name}'s fund portfolio`}</h2></div>
        {normalized.error ? (
          <p className="mt-3 text-sm leading-6 text-amber-300">{normalized.error}</p>
        ) : (
          <>
            <p className="mt-2 text-xs leading-5 text-secondary-text">{language === 'zh' ? '以下占比只在浏览器内由持有金额归一化；金额不会进入请求。切换用户或修改持仓后，本页结果立即清空。' : 'Weights are normalized in-browser; holding amounts never enter the request. Results clear after a user or holding change.'}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {normalized.positions.map((item) => <span key={item.code} className="rounded-full border border-border px-3 py-1 text-xs text-foreground">{item.code} · {item.weightPct.toFixed(2)}%{item.targetWeightPct == null ? '' : ` / 目标 ${item.targetWeightPct}%`}</span>)}
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
              <label className="text-sm text-secondary-text">
                <span className="mb-1 block">{language === 'zh' ? '风险偏好（仅调整关注阈值）' : 'Risk profile (thresholds only)'}</span>
                <select aria-label={language === 'zh' ? '风险偏好' : 'Risk profile'} className="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground" value={riskProfile} onChange={(event) => { setRiskProfile(event.target.value as FundRiskProfile); setResponse(null); setError(''); }}>
                  {(Object.keys(PROFILE_LABELS[language]) as FundRiskProfile[]).map((profile) => <option key={profile} value={profile}>{PROFILE_LABELS[language][profile]}</option>)}
                </select>
              </label>
              <button type="button" className="btn-primary flex min-w-44 items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50" disabled={!approved || loading} onClick={run}>
                {loading && <LoaderCircle className="h-4 w-4 animate-spin" />}
                {loading ? (language === 'zh' ? '分析中' : 'Analyzing') : (language === 'zh' ? '分析当前组合' : 'Analyze portfolio')}
              </button>
            </div>
            <label className="mt-3 flex items-start gap-2 text-xs leading-5 text-secondary-text">
              <input type="checkbox" className="mt-1" checked={approved} onChange={(event) => setApproved(event.target.checked)} />
              <span>{language === 'zh' ? '我确认本次只发送基金代码、归一化占比和目标仓位，在本机读取公开证据并内存计算；不读账户、不交易、不通知、不调用 AI、不保存。' : 'I approve sending fund codes, normalized weights, and target weights to the local public-evidence calculation only: no account read, trading, notifications, AI, or persistence.'}</span>
            </label>
          </>
        )}
        {error && <p className="mt-3 text-sm text-red-400" role="alert">{error}</p>}
      </Card>

      {advice && (
        <div className="space-y-4" data-testid="fund-portfolio-advice-result">
          <Card padding="md">
            <div className="flex flex-wrap gap-2 text-xs text-secondary-text">
              <span className="rounded-full border border-border px-3 py-1">{response?.providerLabel}</span>
              <span>{language === 'zh' ? '读取时间' : 'Fetched'}：{advice.fetched_at}</span>
              <span>{language === 'zh' ? '风险偏好' : 'Risk profile'}：{PROFILE_LABELS[language][advice.risk_profile]}</span>
              <span>{language === 'zh' ? '金额/成本/用户身份未发送' : 'No amount/cost/user identity sent'}</span>
            </div>
          </Card>

          <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {[
              ['基金集中度', advice.concentration.status, `最大 ${value(advice.concentration.largest_fund_weight_pct)} · 前二 ${value(advice.concentration.top_two_weight_pct)}`, Scale],
              ['披露重合', advice.disclosed_overlap.status, `持仓 ${value(advice.disclosed_overlap.max_disclosed_holdings_overlap_pct)} · 行业 ${value(advice.disclosed_overlap.max_disclosed_industry_overlap_pct)}`, Layers3],
              ['行业集中', advice.industry_exposure.status, `前三 ${value(advice.industry_exposure.top_three_exposure_pct)} · 覆盖 ${value(advice.industry_exposure.disclosed_portfolio_coverage_pct)}`, Layers3],
              ['净值风险', advice.nav_risk.status, `波动 ${value(advice.nav_risk.weighted_average_fund_volatility_60d_pct)} · 最差回撤 ${value(advice.nav_risk.worst_fund_drawdown_120d_pct)}`, Waves],
              ['周期压力', advice.cycle_exposure.status, `压力暴露 ${value(advice.cycle_exposure.pressure_exposure_pct)} · 覆盖 ${value(advice.cycle_exposure.analyzed_portfolio_exposure_pct)}`, ShieldAlert],
            ].map(([title, status, summary, Icon]) => {
              const RiskIcon = Icon as typeof Scale;
              return <Card key={title as string} padding="md"><RiskIcon className="h-5 w-5 text-cyan" /><div className="mt-3 flex items-center justify-between gap-2"><h2 className="text-sm font-semibold text-foreground">{title as string}</h2><StatusBadge status={status as FundRiskDimensionStatus} language={language} /></div><p className="mt-2 text-xs leading-5 text-secondary-text">{summary as string}</p></Card>;
            })}
          </section>

          <Card padding="md">
            <h2 className="font-semibold text-foreground">{language === 'zh' ? '披露行业穿透（组合占比）' : 'Disclosed industry look-through'}</h2>
            <p className="mt-2 text-xs text-secondary-text">{language === 'zh' ? `未披露或未分类 ${value(advice.industry_exposure.unclassified_or_undisclosed_pct)}；未知部分不会被强行归类。` : `${value(advice.industry_exposure.unclassified_or_undisclosed_pct)} remains undisclosed or unclassified.`}</p>
            <div className="mt-3 flex flex-wrap gap-2">{advice.industry_exposure.top_industries.map((item) => <span key={item.industry_name} className="rounded-full border border-border px-3 py-1 text-xs text-foreground">{item.industry_name} {item.portfolio_exposure_pct}%</span>)}</div>
          </Card>

          <Card padding="md">
            <h2 className="font-semibold text-foreground">{language === 'zh' ? '逐只基金净值证据' : 'Fund NAV evidence'}</h2>
            <div className="mt-3 overflow-x-auto"><table className="w-full min-w-160 text-left text-xs"><thead className="text-secondary-text"><tr><th className="py-2">{language === 'zh' ? '代码' : 'Code'}</th><th>{language === 'zh' ? '日期' : 'Date'}</th><th>20d</th><th>60d</th><th>{language === 'zh' ? '年化波动' : 'Annualized volatility'}</th><th>{language === 'zh' ? '最大回撤' : 'Max drawdown'}</th></tr></thead><tbody>{advice.nav_risk.funds.map((item) => <tr key={item.code} className="border-t border-border"><td className="py-2 text-foreground">{item.code}</td><td>{item.as_of_date ?? '缺失'}</td><td>{value(item.return_20d_pct)}</td><td>{value(item.return_60d_pct)}</td><td>{value(item.annualized_volatility_60d_pct)}</td><td>{value(item.max_drawdown_120d_pct)}</td></tr>)}</tbody></table></div>
          </Card>

          <Card padding="md" variant="gradient">
            <h2 className="font-semibold text-foreground">{language === 'zh' ? '配置复核建议' : 'Allocation review guidance'}</h2>
            <div className="mt-4 space-y-3">{advice.allocation_guidance.map((item) => <div key={item.id} className="rounded-lg border border-border p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-semibold text-foreground">{item.title}</h3><span className="text-xs text-secondary-text">{item.priority}</span></div><p className="mt-2 text-xs leading-5 text-secondary-text">{item.reason}</p><p className="mt-2 text-xs leading-5 text-foreground">{item.action}</p><p className="mt-2 text-xs text-secondary-text">{item.evidence.join(' · ')}</p></div>)}</div>
          </Card>

          {[...advice.missing_evidence, ...advice.warnings].length > 0 && <Card padding="md"><p className="text-xs leading-5 text-amber-300">{[...advice.missing_evidence.map((item) => `缺失: ${item}`), ...advice.warnings].join('；')}</p></Card>}
        </div>
      )}
    </div>
  );
};

export default FundPortfolioAdvicePanel;
