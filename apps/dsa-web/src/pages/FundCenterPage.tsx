import type React from 'react';
import { ArrowRight, BookOpenCheck, GitCompareArrows, Landmark, Layers3, MessageCircleQuestion, ShieldAlert, TrendingUp } from 'lucide-react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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

  useEffect(() => { document.title = `${title} - 股票基金质量分析系统`; }, [title]);

  return (
    <div className="min-h-screen space-y-5 p-4 md:p-6" data-testid={`fund-center-${section}`}>
      <section className="space-y-2">
        <div className="flex items-center gap-3"><Landmark className="h-6 w-6 text-cyan" /><h1 className="text-xl font-semibold text-foreground md:text-2xl">{title}</h1></div>
        <p className="text-sm leading-6 text-secondary-text">{description}</p>
        <p className="text-xs text-secondary-text">{language === 'zh' ? '当前用户' : 'Current user'}：<span className="font-medium text-foreground">{activeUser.name}</span></p>
      </section>

      <InlineAlert
        variant="info"
        title={language === 'zh' ? '基金数据契约已建立，真实数据尚未接入' : 'Fund data contracts are ready; real data is not connected'}
        message={language === 'zh'
          ? 'Build C 已定义基金资料、净值、披露持仓、行业映射及来源元数据。正式运行只返回“未接入/缺失”状态，不使用测试 fixture，不发起真实 Provider 请求。'
          : 'Build C defines fund profiles, NAV, disclosed holdings, industry mapping, and provenance. Production returns an explicit not-connected/missing state, does not use test fixtures, and makes no real provider request.'}
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
            title={language === 'zh' ? '数据契约已准备，分析能力等待 Build D' : 'Data contracts are ready; analysis follows in Build D'}
            description={language === 'zh' ? '当前只显示可审计的缺失状态，不生成虚假基金对比、行业周期或买卖建议。' : 'The page currently shows an auditable missing state and does not fabricate fund comparisons, industry cycles, or trading suggestions.'}
          />
        </Card>
      )}
    </div>
  );
};

export default FundCenterPage;
