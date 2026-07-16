import type React from 'react';
import { ArrowRight, Landmark, LineChart, UsersRound } from 'lucide-react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, InlineAlert } from '../components/common';
import { usePortfolioUsers } from '../contexts/PortfolioUserContext';
import { useUiLanguage } from '../contexts/UiLanguageContext';

const TEXT = {
  zh: {
    documentTitle: '股票基金质量分析系统', title: '选择分析中心',
    description: '股票和基金使用独立入口、持仓、问答与分析上下文，共用同一个当前用户和系统设置。',
    currentUser: '当前用户', userHint: '切换中心不会切换用户，避免误用其他人的持仓。',
    stocks: '股票中心', stockDescription: '股票分析、问股票、股票持仓、选股策略、AI 建议、回测和告警。',
    funds: '基金中心', fundDescription: '基金持仓、问基金、基金对比、行业穿透、行业周期和风险建议。',
    enter: '进入', manageUsers: '管理用户', boundaryTitle: '当前基金能力边界',
    boundary: '公开基金资料、净值、披露持仓、基金对比和披露行业穿透已接入；行业周期、生产力、配置建议和 AI 仍未接入，不生成虚假结果。',
  },
  en: {
    documentTitle: 'Stock and Fund Quality Analysis', title: 'Choose a workspace',
    description: 'Stocks and funds have separate navigation, holdings, Q&A, and analysis context while sharing the active user and system settings.',
    currentUser: 'Current user', userHint: 'Changing workspaces keeps the same user to prevent cross-user portfolio use.',
    stocks: 'Stock center', stockDescription: 'Stock analysis, stock Q&A, holdings, screening, AI signals, backtests, and alerts.',
    funds: 'Fund center', fundDescription: 'Fund holdings, fund Q&A, comparisons, industry exposure, cycles, and risk guidance.',
    enter: 'Open', manageUsers: 'Manage users', boundaryTitle: 'Current fund capability boundary',
    boundary: 'Public profiles, NAV, disclosed holdings, fund comparison, and disclosed industry exposure are connected. Cycles, productivity, allocation advice, and AI remain unavailable and are never fabricated.',
  },
} as const;

const WorkspaceLandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { language } = useUiLanguage();
  const { activeUser } = usePortfolioUsers();
  const text = TEXT[language];

  useEffect(() => { document.title = text.documentTitle; }, [text.documentTitle]);

  return (
    <div className="min-h-screen space-y-6 p-4 md:p-8" data-testid="workspace-landing-page">
      <section className="mx-auto max-w-5xl space-y-3 pt-4 md:pt-10">
        <p className="text-sm text-cyan">{text.currentUser}：<span className="font-semibold text-foreground">{activeUser.name}</span></p>
        <h1 className="text-2xl font-semibold text-foreground md:text-4xl">{text.title}</h1>
        <p className="max-w-3xl text-sm leading-7 text-secondary-text md:text-base">{text.description}</p>
        <p className="text-xs text-secondary-text">{text.userHint}</p>
      </section>

      <section className="mx-auto grid max-w-5xl gap-4 md:grid-cols-2" aria-label={text.title}>
        {([
          { key: 'stocks', title: text.stocks, description: text.stockDescription, icon: LineChart, path: '/stocks' },
          { key: 'funds', title: text.funds, description: text.fundDescription, icon: Landmark, path: '/funds' },
        ] as const).map(({ key, title, description, icon: Icon, path }) => (
          <Card key={key} variant="gradient" padding="lg" className="flex min-h-64 flex-col justify-between">
            <div>
              <Icon className="h-9 w-9 text-cyan" aria-hidden="true" />
              <h2 className="mt-5 text-xl font-semibold text-foreground">{title}</h2>
              <p className="mt-3 text-sm leading-7 text-secondary-text">{description}</p>
            </div>
            <button type="button" className="btn-primary mt-6 flex items-center justify-center gap-2" onClick={() => navigate(path)}>
              {text.enter}{title}<ArrowRight className="h-4 w-4" />
            </button>
          </Card>
        ))}
      </section>

      <section className="mx-auto max-w-5xl space-y-3">
        <InlineAlert variant="info" title={text.boundaryTitle} message={text.boundary} />
        <button type="button" className="btn-secondary flex items-center gap-2 text-sm" onClick={() => navigate('/users')}>
          <UsersRound className="h-4 w-4" />{text.manageUsers}
        </button>
      </section>
    </div>
  );
};

export default WorkspaceLandingPage;
