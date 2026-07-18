import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SidebarNav } from '../SidebarNav';

const mockLogout = vi.fn().mockResolvedValue(undefined);
const mockGetAlphaSiftStatus = vi.fn().mockResolvedValue({ enabled: false, available: false, installSpecIsDefault: false });
const mockThemeToggle = vi.fn(({ collapsed }: { collapsed?: boolean }) => (
  <button type="button">{collapsed ? '切换主题(折叠)' : '切换主题'}</button>
));

const completionBadgeState = { value: true };

vi.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    authEnabled: true,
    logout: mockLogout,
  }),
}));

vi.mock('../../../stores/agentChatStore', () => ({
  useAgentChatStore: (selector: (state: { completionBadge: boolean }) => unknown) =>
    selector({ completionBadge: completionBadgeState.value }),
}));

vi.mock('../../../api/alphasift', () => ({
  ALPHASIFT_CONFIG_CHANGED_EVENT: 'alphasift-config-changed',
  SYSTEM_CONFIG_CHANGED_EVENT: 'dsa-system-config-changed',
  alphasiftApi: {
    getStatus: () => mockGetAlphaSiftStatus(),
  },
}));

vi.mock('../../theme/ThemeToggle', () => ({
  ThemeToggle: (props: { collapsed?: boolean }) => mockThemeToggle(props),
}));

describe('SidebarNav', () => {
  it('keeps all center entries reachable in short windows through internal scrolling', () => {
    render(<MemoryRouter initialEntries={['/funds']}><SidebarNav /></MemoryRouter>);
    const navigation = screen.getByRole('navigation', { name: '主导航' });
    expect(navigation.className).toContain('overflow-y-auto');
    expect(screen.getByRole('link', { name: '基金首页' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '基金建议' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '用户管理' })).toBeInTheDocument();
  });
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    completionBadgeState.value = true;
    mockGetAlphaSiftStatus.mockResolvedValue({ enabled: false, available: false, installSpecIsDefault: false });
  });

  it('hides the screening navigation item while AlphaSift is disabled', () => {
    mockGetAlphaSiftStatus.mockResolvedValueOnce({ enabled: false, available: false, installSpecIsDefault: false });

    render(
      <MemoryRouter initialEntries={['/']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    expect(screen.queryByRole('link', { name: '选股' })).not.toBeInTheDocument();
  });

  it('shows the screening navigation item when AlphaSift is enabled', async () => {
    mockGetAlphaSiftStatus.mockResolvedValueOnce({ enabled: true, available: false, installSpecIsDefault: false });

    render(
      <MemoryRouter initialEntries={['/']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    expect(await screen.findByRole('link', { name: '选股策略' })).toHaveAttribute('href', '/stocks/screening');
  });

  it('places screening directly after chat when AlphaSift is enabled', async () => {
    mockGetAlphaSiftStatus.mockResolvedValueOnce({ enabled: true, available: false, installSpecIsDefault: false });

    render(
      <MemoryRouter initialEntries={['/']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    await screen.findByRole('link', { name: '选股策略' });
    const hrefs = screen.getAllByRole('link').map((link) => link.getAttribute('href'));
    expect(hrefs.slice(0, 5)).toEqual(['/stocks', '/stocks/ask', '/stocks/screening', '/stocks/portfolio', '/stocks/advice']);
  });

  it('keeps settings between backtest and theme while preserving existing navigation entries', () => {
    mockGetAlphaSiftStatus.mockResolvedValueOnce({ enabled: false, available: false, installSpecIsDefault: false });

    render(
      <MemoryRouter initialEntries={['/settings']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    const labels = screen.getAllByRole('link').map((link) => link.getAttribute('aria-label'));
    expect(labels).toEqual(['股票首页', '问股票', '股票持仓', '股票建议', '股票回测', '股票告警', '设置', '用量', '用户管理']);
    expect(screen.getByRole('link', { name: '设置' })).toHaveAttribute('href', '/settings');
    expect(screen.getByRole('link', { name: '设置' })).toHaveClass('font-medium');
    expect(screen.getByRole('button', { name: '切换主题' })).toBeInTheDocument();
  });

  it('refreshes the screening navigation item after any config save event', async () => {
    mockGetAlphaSiftStatus
      .mockResolvedValueOnce({ enabled: false, available: false, installSpecIsDefault: false })
      .mockResolvedValueOnce({ enabled: true, available: false, installSpecIsDefault: false });

    render(
      <MemoryRouter initialEntries={['/']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    expect(screen.queryByRole('link', { name: '选股' })).not.toBeInTheDocument();
    window.dispatchEvent(new Event('dsa-system-config-changed'));

    expect(await screen.findByRole('link', { name: '选股策略' })).toHaveAttribute('href', '/stocks/screening');
    await waitFor(() => expect(mockGetAlphaSiftStatus.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it('shows the shared completion badge only when chat completion is pending', () => {
    completionBadgeState.value = true;

    const { rerender } = render(
      <MemoryRouter initialEntries={['/stocks/ask']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    expect(screen.getByTestId('chat-completion-badge')).toBeInTheDocument();
    expect(screen.getByLabelText('问股票有新消息')).toBeInTheDocument();

    completionBadgeState.value = false;
    rerender(
      <MemoryRouter initialEntries={['/stocks/ask']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    expect(screen.queryByTestId('chat-completion-badge')).not.toBeInTheDocument();
  });

  it('renders the collapsed theme toggle variant when the sidebar is collapsed', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <SidebarNav collapsed />
      </MemoryRouter>,
    );

    expect(mockThemeToggle).toHaveBeenCalledWith(
      expect.objectContaining({ variant: 'nav', collapsed: true }),
    );
    expect(screen.getByRole('button', { name: '切换主题(折叠)' })).toBeInTheDocument();
  });

  it('renders the alerts navigation item and marks it active', () => {
    render(
      <MemoryRouter initialEntries={['/stocks/alerts']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    const alertsLink = screen.getByRole('link', { name: '股票告警' });
    expect(alertsLink).toHaveAttribute('href', '/stocks/alerts');
    expect(alertsLink).toHaveClass('font-medium');
  });

  it('renders the AI signals navigation item and marks it active', () => {
    render(
      <MemoryRouter initialEntries={['/stocks/advice']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    const signalsLink = screen.getByRole('link', { name: '股票建议' });
    expect(signalsLink).toHaveAttribute('href', '/stocks/advice');
    expect(signalsLink).toHaveClass('font-medium');
  });

  it('opens the logout confirmation and confirms logout', async () => {
    render(
      <MemoryRouter initialEntries={['/stocks/ask']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole('button', { name: '退出' }));

    expect(await screen.findByRole('heading', { name: '退出登录' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '确认退出' }));
    expect(mockLogout).toHaveBeenCalled();
  });

  it('shows fund-only navigation after switching to the fund center', () => {
    render(
      <MemoryRouter initialEntries={['/funds']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: '问基金' })).toHaveAttribute('href', '/funds/ask');
    expect(screen.getByRole('link', { name: '基金持仓' })).toHaveAttribute('href', '/funds/portfolio');
    expect(screen.getByRole('link', { name: '行业周期' })).toHaveAttribute('href', '/funds/industry-cycle');
    expect(screen.queryByRole('link', { name: '问股票' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: '股票回测' })).not.toBeInTheDocument();
  });
});
