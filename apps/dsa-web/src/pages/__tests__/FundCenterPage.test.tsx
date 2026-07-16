import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { PortfolioUserProvider } from '../../contexts/PortfolioUserContext';
import { UiLanguageProvider } from '../../contexts/UiLanguageContext';
import { UI_LANGUAGE_STORAGE_KEY } from '../../utils/uiLanguage';
import FundCenterPage from '../FundCenterPage';

function renderPage(section: 'home' | 'ask' | 'industry-cycle') {
  render(
    <UiLanguageProvider>
      <PortfolioUserProvider>
        <MemoryRouter><FundCenterPage section={section} /></MemoryRouter>
      </PortfolioUserProvider>
    </UiLanguageProvider>,
  );
}

describe('FundCenterPage', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, 'zh');
  });

  it('shows fund-only tasks and the real-data boundary on the fund home', () => {
    renderPage('home');

    expect(screen.getByRole('heading', { name: '基金首页' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /进入基金持仓/ })).toBeInTheDocument();
    expect(screen.getByText('真实基金数据尚未接入')).toBeInTheDocument();
    expect(screen.queryByText('股票回测')).not.toBeInTheDocument();
  });

  it('keeps fund questions separate from the stock chat implementation', () => {
    renderPage('ask');

    expect(screen.getByRole('heading', { name: '问基金' })).toBeInTheDocument();
    expect(screen.getByText(/不会请求真实净值、持仓或 Provider/)).toBeInTheDocument();
    expect(screen.getByText(/当前只显示安全空状态/)).toBeInTheDocument();
  });

  it('describes the required evidence boundary for industry cycles', () => {
    renderPage('industry-cycle');

    expect(screen.getByText(/证据、日期、周期阶段、置信度和缺失项/)).toBeInTheDocument();
  });
});
