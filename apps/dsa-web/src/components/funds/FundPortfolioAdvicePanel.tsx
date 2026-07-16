import { AlertTriangle, LoaderCircle, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { fundDataApi, type FundPortfolioAdviceReadonlyResponse } from '../../api/fundData';
import type { QuickFundHolding } from '../../contexts/PortfolioUserContext';
import { Card, InlineAlert } from '../common';

type Props = {
  language: 'zh' | 'en';
  activeUserName: string;
  holdings: readonly QuickFundHolding[];
};

const RISK_LABELS = {
  zh: { high: '高', medium: '中', low: '低', insufficient: '证据不足' },
  en: { high: 'High', medium: 'Medium', low: 'Low', insufficient: 'Insufficient evidence' },
} as const;

const FundPortfolioAdvicePanel = ({ language, activeUserName, holdings }: Props) => {
  const [approved, setApproved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [response, setResponse] = useState<FundPortfolioAdviceReadonlyResponse | null>(null);
  const validHoldings = holdings.length > 0 && holdings.length <= 20
    && holdings.every((item) => /^\d{6}$/.test(item.code) && Number.isFinite(item.amount) && item.amount > 0);

  const run = async () => {
    if (!approved || !validHoldings || loading) return;
    setLoading(true);
    setError('');
    setResponse(null);
    try {
      const result = await fundDataApi.fetchAkshareFundPortfolioAdvice(holdings.map((item) => ({
        code: item.code,
        name: item.name,
        amount: item.amount,
        profit: item.profit,
        targetAllocation: item.targetAllocation,
      })));
      setResponse(result);
      if (result.status !== 'completed-readonly') {
        setError(language === 'zh' ? '组合证据暂时不可用，请稍后重试。' : 'Portfolio evidence is unavailable. Please retry later.');
      }
    } catch {
      setError(language === 'zh' ? '组合风险计算失败，未保存任何数据。' : 'Portfolio risk calculation failed. No data was saved.');
    } finally {
      setLoading(false);
    }
  };

  const advice = response?.advice;
  return (
    <div className="space-y-4">
      <InlineAlert
        variant="info"
        title={language === 'zh' ? 'Build D4 当前用户基金组合风险与配置建议' : 'Build D4 active-user fund portfolio risk and allocation guidance'}
        message={language === 'zh'
          ? '组合权重使用当前页面内存持仓；仅把金额最大的前 4 只基金代码用于公开证据补充，金额不会发送给 AKShare。结果是人工复核建议，不是买卖指令。'
          : 'Weights use the current in-memory holdings. Only the top four fund codes are used for public evidence; amounts are never sent to AKShare. Results are review guidance, not orders.'}
      />
      <Card padding="md">
        <h2 className="font-semibold text-foreground">{language === 'zh' ? `${activeUserName}的基金组合` : `${activeUserName}'s fund portfolio`}</h2>
        <p className="mt-2 text-sm text-secondary-text">{language === 'zh' ? `当前录入 ${holdings.length} 条基金持仓。刷新后仍会清空。` : `${holdings.length} fund holdings are currently entered. Refresh still clears them.`}</p>
        {holdings.length === 0 && <p className="mt-3 text-sm text-amber-300">{language === 'zh' ? '请先到“基金持仓”录入当前用户的基金。' : 'Add funds on Fund holdings first.'}</p>}
        {holdings.length > 20 && <p className="mt-3 text-sm text-amber-300">{language === 'zh' ? '当前最多分析 20 条持仓，请先整理重复记录。' : 'Up to 20 holdings are supported; consolidate duplicates first.'}</p>}
        <label className="mt-4 flex items-start gap-2 text-xs leading-5 text-secondary-text">
          <input type="checkbox" className="mt-1" checked={approved} onChange={(event) => setApproved(event.target.checked)} />
          <span>{language === 'zh' ? '我确认本次只在本机计算当前页面基金组合，并逐次读取公开基金/行业证据；不读账户、不交易、不通知、不调用 AI、不保存。' : 'I approve this local in-memory calculation and public evidence lookup only: no account access, trading, notifications, AI, or persistence.'}</span>
        </label>
        <button type="button" className="btn-primary mt-4 flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50" disabled={!approved || !validHoldings || loading} onClick={run}>
          {loading && <LoaderCircle className="h-4 w-4 animate-spin" />}
          {loading ? (language === 'zh' ? '计算中' : 'Calculating') : (language === 'zh' ? '计算组合风险' : 'Calculate portfolio risk')}
        </button>
        {error && <p className="mt-3 text-sm text-red-400" role="alert">{error}</p>}
      </Card>

      {advice && (
        <div className="space-y-4" data-testid="fund-portfolio-advice-result">
          <Card padding="md">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><p className="text-xs text-secondary-text">{language === 'zh' ? '组合风险等级' : 'Portfolio risk level'}</p><p className="mt-1 text-xl font-semibold text-foreground">{RISK_LABELS[language][advice.risk_level]}</p></div>
              <ShieldCheck className="h-7 w-7 text-cyan" />
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4 text-sm">
              <span>{language === 'zh' ? '基金总额' : 'Fund total'}：{advice.total_amount}</span>
              <span>{language === 'zh' ? '最大单只' : 'Largest fund'}：{advice.top_fund_weight_pct}%</span>
              <span>{language === 'zh' ? '前三合计' : 'Top three'}：{advice.top3_weight_pct}%</span>
              <span>{language === 'zh' ? '公开证据覆盖' : 'Public evidence coverage'}：{advice.public_evidence_coverage_pct}%</span>
            </div>
          </Card>

          {advice.findings.map((item, index) => (
            <Card key={`${item.category}-${index}`} padding="md">
              <div className="flex items-start gap-3"><AlertTriangle className={`mt-0.5 h-5 w-5 ${item.severity === 'high' ? 'text-red-400' : 'text-amber-300'}`} /><div><h2 className="font-semibold text-foreground">{item.title}</h2><p className="mt-2 text-sm leading-6 text-secondary-text">{item.evidence}</p></div></div>
            </Card>
          ))}

          <Card padding="md">
            <h2 className="font-semibold text-foreground">{language === 'zh' ? '配置复核建议（不自动执行）' : 'Allocation review guidance (not executed)'}</h2>
            <div className="mt-3 space-y-3">
              {advice.suggestions.map((item, index) => <div key={`${item.title}-${index}`} className="rounded-lg border border-border p-3"><p className="text-sm font-medium text-foreground">{item.title}</p><p className="mt-1 text-xs leading-5 text-secondary-text">{item.reason}</p></div>)}
            </div>
          </Card>

          {(advice.missing_evidence.length > 0 || advice.warnings.length > 0) && <Card padding="md"><h2 className="font-semibold text-foreground">{language === 'zh' ? '证据边界' : 'Evidence boundaries'}</h2><p className="mt-2 text-xs leading-5 text-amber-300">{[...advice.missing_evidence.map((item) => `缺失: ${item}`), ...advice.warnings].join('；')}</p></Card>}
        </div>
      )}
    </div>
  );
};

export default FundPortfolioAdvicePanel;
