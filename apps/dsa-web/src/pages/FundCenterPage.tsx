import type React from 'react';
import { ArrowRight, BookOpenCheck, GitCompareArrows, Landmark, Layers3, LoaderCircle, MessageCircleQuestion, ShieldAlert, TrendingUp } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fundDataApi, type FundPublicReadonlyResponse } from '../api/fundData';
import { Card, EmptyState, InlineAlert } from '../components/common';
import { usePortfolioUsers } from '../contexts/PortfolioUserContext';
import { useUiLanguage } from '../contexts/UiLanguageContext';

export type FundCenterSection = 'home' | 'ask' | 'compare' | 'industry-exposure' | 'industry-cycle' | 'advice';

type FundCenterPageProps = { section: FundCenterSection };

const SECTION_META = {
  zh: {
    home: ['基金首页', '查看当前用户的基金任务、持仓入口、行业分析入口和数据状态。'],
    ask: ['问基金', '只处理基金代码、基金名称、持仓、行业暴露、周期和配置问题。'],
    compare: ['基金筛选与对比', '对比基金类型、行业集中度、持仓重复度、风险和数据日期。'],
    'industry-exposure': ['行业持仓穿透', '按披露报告期查看基金持仓和行业映射，未知行业保持未知。'],
    'industry-cycle': ['行业周期与景气度', '按证据、日期、周期阶段、置信度和缺失项展示行业判断。'],
    advice: ['基金仓位与风险建议', '基于当前用户基金持仓区分事实、推断、风险提示和非自动执行建议。'],
  },
  en: {
    home: ['Fund home', 'Review fund tasks, holdings, industry analysis entries, and data status for the active user.'],
    ask: ['Ask about funds', 'Handles fund identifiers, holdings, industry exposure, cycles, and allocation questions only.'],
    compare: ['Fund screening and comparison', 'Compare type, industry concentration, overlap, risk, and data dates.'],
    'industry-exposure': ['Industry exposure', 'Review disclosed holdings and industry mapping by report period while preserving unknown classifications.'],
    'industry-cycle': ['Industry cycles', 'Show evidence, date, cycle stage, confidence, and missing inputs.'],
    advice: ['Fund allocation and risk', 'Separate facts, inference, risk, and non-executing suggestions for the active user.'],
  },
} as const;

const HOME_LINKS = [
  { section: 'ask', icon: MessageCircleQuestion, path: '/funds/ask' },
  { section: 'compare', icon: GitCompareArrows, path: '/funds/compare' },
  { section: 'industry-exposure', icon: Layers3, path: '/funds/industry-exposure' },
  { section: 'industry-cycle', icon: TrendingUp, path: '/funds/industry-cycle' },
  { section: 'advice', icon: ShieldAlert, path: '/funds/advice' },
] as const;

const FundCenterPage: React.FC<FundCenterPageProps> = ({ section }) => {
  const navigate = useNavigate();
  const { language } = useUiLanguage();
  const { activeUser } = usePortfolioUsers();
  const [title, description] = SECTION_META[language][section];
  const isHome = section === 'home';
  const [fundCode, setFundCode] = useState('');
  const [readOnlyApproved, setReadOnlyApproved] = useState(false);
  const [lookupResult, setLookupResult] = useState<FundPublicReadonlyResponse | null>(null);
  const [lookupError, setLookupError] = useState('');
  const [lookupLoading, setLookupLoading] = useState(false);
  const validFundCode = /^\d{6}$/.test(fundCode);

  useEffect(() => { document.title = `${title} - 股票基金质量分析系统`; }, [title]);

  const runFundLookup = async () => {
    if (!validFundCode || !readOnlyApproved || lookupLoading) return;
    setLookupLoading(true);
    setLookupError('');
    setLookupResult(null);
    try {
      const result = await fundDataApi.fetchAksharePublicFund(fundCode);
      setLookupResult(result);
      if (result.status !== 'completed-readonly') {
        setLookupError(language === 'zh' ? '公开基金数据暂时不可用，请稍后重试。' : 'Public fund data is currently unavailable. Please try again later.');
      }
    } catch {
      setLookupError(language === 'zh' ? '公开基金数据读取失败，未保存任何数据。' : 'Public fund data lookup failed. No data was saved.');
    } finally {
      setLookupLoading(false);
    }
  };

  return (
    <div className="min-h-screen space-y-5 p-4 md:p-6" data-testid={`fund-center-${section}`}>
      <section className="space-y-2">
        <div className="flex items-center gap-3"><Landmark className="h-6 w-6 text-cyan" /><h1 className="text-xl font-semibold text-foreground md:text-2xl">{title}</h1></div>
        <p className="text-sm leading-6 text-secondary-text">{description}</p>
        <p className="text-xs text-secondary-text">{language === 'zh' ? '当前用户' : 'Current user'}：<span className="font-medium text-foreground">{activeUser.name}</span></p>
      </section>

      <InlineAlert
        variant="info"
        title={language === 'zh' ? 'AKShare 基金公开数据支持本机手动只读查询' : 'AKShare public fund data supports manual local read-only lookup'}
        message={language === 'zh'
          ? 'Build D1 仅在您输入六位基金代码并逐次确认后读取公开资料、正式净值和披露持仓；不读取账户，不调用 AI，不通知、不交易、不持久化。'
          : 'Build D1 reads public profile, official NAV, and disclosed holdings only after you enter a six-digit fund code and approve each request. It does not read accounts, call AI, notify, trade, or persist data.'}
      />

      <Card padding="md">
        <h2 className="font-semibold text-foreground">{language === 'zh' ? 'Build C 基金数据契约' : 'Build C fund data contract'}</h2>
        <p className="mt-2 text-sm leading-6 text-secondary-text">
          {language === 'zh'
            ? '未来每条基金事实必须携带来源、抓取时间、生效日或报告期、过期状态、置信度以及字段级缺失原因；未知行业保持未知。'
            : 'Every future fund fact must carry its source, fetch time, effective date or report period, stale state, confidence, and field-level missing reasons. Unknown industries remain unknown.'}
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-secondary-text">
          {(language === 'zh'
            ? ['基金资料', '净值快照', '披露持仓', '行业映射']
            : ['Fund profile', 'NAV snapshot', 'Disclosed holdings', 'Industry mapping']
          ).map((item) => <span key={item} className="rounded-full border border-border px-3 py-1">{item}</span>)}
        </div>
      </Card>

      {isHome ? (
        <>
          <Card padding="md">
            <h2 className="font-semibold text-foreground">{language === 'zh' ? '读取公开基金数据' : 'Read public fund data'}</h2>
            <p className="mt-2 text-sm leading-6 text-secondary-text">
              {language === 'zh' ? '数据来自 AKShare 公共接口，仅保存在当前页面内存中。行业映射等待 Build D2，未知行业不会被强行归类。' : 'Data comes from public AKShare interfaces and remains in page memory only. Industry mapping follows in Build D2; unknown industries are never forced into a category.'}
            </p>
            <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-end">
              <label className="flex-1 text-sm text-secondary-text">
                <span className="mb-1 block">{language === 'zh' ? '六位基金代码' : 'Six-digit fund code'}</span>
                <input
                  aria-label={language === 'zh' ? '六位基金代码' : 'Six-digit fund code'}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground outline-none focus:border-cyan"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="例如 000001"
                  value={fundCode}
                  onChange={(event) => {
                    setFundCode(event.target.value.replace(/\D/g, '').slice(0, 6));
                    setLookupResult(null);
                    setLookupError('');
                  }}
                />
              </label>
              <button
                type="button"
                className="btn-primary flex min-w-40 items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!validFundCode || !readOnlyApproved || lookupLoading}
                onClick={runFundLookup}
              >
                {lookupLoading && <LoaderCircle className="h-4 w-4 animate-spin" />}
                {lookupLoading ? (language === 'zh' ? '读取中' : 'Loading') : (language === 'zh' ? '手动读取' : 'Read now')}
              </button>
            </div>
            <label className="mt-3 flex items-start gap-2 text-xs leading-5 text-secondary-text">
              <input
                type="checkbox"
                className="mt-1"
                checked={readOnlyApproved}
                onChange={(event) => setReadOnlyApproved(event.target.checked)}
              />
              <span>{language === 'zh' ? '我确认本次仅获取公开只读基金数据，不读取账户、不交易、不通知、不调用 AI、不保存。' : 'I approve this public read-only lookup only: no account access, trading, notifications, AI, or persistence.'}</span>
            </label>
            {lookupError && <p className="mt-3 text-sm text-red-400" role="alert">{lookupError}</p>}
            {lookupResult?.status === 'completed-readonly' && lookupResult.bundle && (
              <div className="mt-5 space-y-4" data-testid="fund-public-readonly-result">
                <div className="flex flex-wrap items-center gap-2 text-xs text-secondary-text">
                  <span className="rounded-full border border-border px-3 py-1">{lookupResult.providerLabel}</span>
                  <span>{language === 'zh' ? '读取时间' : 'Fetched'}：{lookupResult.bundle.source.fetched_at}</span>
                  <span>{language === 'zh' ? '状态' : 'Status'}：{lookupResult.bundle.data_status}</span>
                </div>
                {(lookupResult.bundle.reason || lookupResult.bundle.missing_sections.length > 0) && (
                  <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-300">
                    {lookupResult.bundle.reason || (language === 'zh' ? '部分数据区块缺失。' : 'Some data sections are missing.')}
                    {lookupResult.bundle.missing_sections.length > 0 && ` ${language === 'zh' ? '缺失区块' : 'Missing'}：${lookupResult.bundle.missing_sections.join(', ')}`}
                  </p>
                )}
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{language === 'zh' ? '基金名称' : 'Fund'}</p><p className="mt-1 font-medium text-foreground">{lookupResult.bundle.profile?.name ?? '缺失'}</p></div>
                  <div className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{language === 'zh' ? '基金类型' : 'Type'}</p><p className="mt-1 font-medium text-foreground">{lookupResult.bundle.profile?.fund_type ?? '缺失'}</p></div>
                  <div className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{language === 'zh' ? '单位净值' : 'Unit NAV'}</p><p className="mt-1 font-medium text-foreground">{lookupResult.bundle.nav?.unit_nav ?? '缺失'}</p></div>
                  <div className="rounded-lg border border-border p-3"><p className="text-xs text-secondary-text">{language === 'zh' ? '净值日期' : 'NAV date'}</p><p className="mt-1 font-medium text-foreground">{lookupResult.bundle.nav?.nav_date ?? '缺失'}</p></div>
                </div>
                {lookupResult.bundle.holdings && (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">{language === 'zh' ? '最新披露前十大持仓' : 'Latest disclosed top holdings'} · {lookupResult.bundle.holdings.report_period}</h3>
                    <div className="mt-2 overflow-x-auto">
                      <table className="w-full min-w-128 text-left text-xs">
                        <thead className="text-secondary-text"><tr><th className="py-2">{language === 'zh' ? '代码' : 'Code'}</th><th>{language === 'zh' ? '名称' : 'Name'}</th><th>{language === 'zh' ? '权重' : 'Weight'}</th><th>{language === 'zh' ? '行业' : 'Industry'}</th></tr></thead>
                        <tbody>
                          {lookupResult.bundle.holdings.positions.map((position) => (
                            <tr key={position.security_code} className="border-t border-border">
                              <td className="py-2 text-foreground">{position.security_code}</td>
                              <td className="text-foreground">{position.security_name}</td>
                              <td className="text-foreground">{position.weight_pct}%</td>
                              <td className="text-secondary-text">{position.industry.industry_name ?? (language === 'zh' ? '待 D2 映射' : 'Pending D2')}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </Card>
          <Card padding="md" variant="gradient">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div><h2 className="font-semibold text-foreground">{language === 'zh' ? '基金持仓' : 'Fund holdings'}</h2><p className="mt-1 text-sm text-secondary-text">{language === 'zh' ? '查看和快速录入当前用户的基金持仓。' : 'Review and quick-enter fund holdings for the active user.'}</p></div>
              <button type="button" className="btn-primary flex items-center gap-2" onClick={() => navigate('/funds/portfolio')}>{language === 'zh' ? '进入基金持仓' : 'Open fund holdings'}<ArrowRight className="h-4 w-4" /></button>
            </div>
          </Card>
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {HOME_LINKS.map(({ section: target, icon: Icon, path }) => {
              const [itemTitle, itemDescription] = SECTION_META[language][target];
              return <Card key={target} padding="md"><Icon className="h-5 w-5 text-cyan" /><h2 className="mt-3 font-semibold text-foreground">{itemTitle}</h2><p className="mt-2 min-h-12 text-xs leading-5 text-secondary-text">{itemDescription}</p><button type="button" className="btn-secondary mt-4 w-full text-sm" onClick={() => navigate(path)}>{language === 'zh' ? '查看入口' : 'Open'}</button></Card>;
            })}
          </section>
        </>
      ) : (
        <Card padding="lg">
          <EmptyState
            icon={<BookOpenCheck className="h-7 w-7" />}
            title={language === 'zh' ? '公开数据入口已建立，分析能力按 Build D 分阶段接入' : 'Public data lookup is ready; analysis follows through Build D'}
            description={language === 'zh' ? 'Build D1 只在基金首页手动读取公开资料、净值和披露持仓；本页仍不生成虚假基金对比、行业周期或买卖建议。' : 'Build D1 reads public profile, NAV, and disclosed holdings manually on the fund home only. This page still does not fabricate comparisons, cycles, or trading suggestions.'}
          />
        </Card>
      )}
    </div>
  );
};

export default FundCenterPage;
