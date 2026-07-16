import type React from 'react';
import { useEffect } from 'react';
import { ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import PortfolioPage from './PortfolioPage';

const TEXT = {
  zh: {
    documentTitle: '股票高级管理 - DSA',
    title: '股票高级管理',
    description: '仅用于股票账户：交易录入、资金流水、公司行为、券商 CSV、账户管理和精确成本核算。',
    back: '返回我的持仓分析',
  },
  en: {
    documentTitle: 'Stock Advanced Management - DSA',
    title: 'Stock advanced management',
    description: 'Stock accounts only: trade entry, cash ledger, corporate actions, broker CSV, account management, and exact cost accounting.',
    back: 'Back to my holdings analysis',
  },
} as const;

const StockPortfolioManagementPage: React.FC = () => {
  const navigate = useNavigate();
  const { language } = useUiLanguage();
  const text = TEXT[language];

  useEffect(() => {
    document.title = text.documentTitle;
  }, [text.documentTitle]);

  return (
    <div className="min-h-screen space-y-4 p-4 md:p-6" data-testid="stock-portfolio-management-page">
      <section className="space-y-3">
        <button
          type="button"
          className="btn-secondary flex items-center gap-2 text-sm"
          onClick={() => navigate('/stocks/portfolio')}
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          {text.back}
        </button>
        <div>
          <h1 className="text-xl font-semibold text-foreground md:text-2xl">{text.title}</h1>
          <p className="mt-1 text-xs leading-6 text-secondary md:text-sm">{text.description}</p>
        </div>
      </section>

      <style>{`
        .stock-portfolio-management-body .portfolio-page {
          min-height: auto;
          padding: 0;
        }
        .stock-portfolio-management-body .portfolio-page > section:first-child > div:first-child {
          display: none;
        }
      `}</style>
      <div className="stock-portfolio-management-body">
        <PortfolioPage />
      </div>
    </div>
  );
};

export default StockPortfolioManagementPage;
