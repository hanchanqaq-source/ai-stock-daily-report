import React, { useEffect, useState } from 'react';
import { Activity, BarChart3, Bell, BriefcaseBusiness, Gauge, GitCompareArrows, Home, Layers3, LogOut, MessageSquareQuote, Search, Settings2, ShieldAlert, TrendingUp, UsersRound } from 'lucide-react';
import { NavLink, useLocation } from 'react-router-dom';
import { ALPHASIFT_CONFIG_CHANGED_EVENT, SYSTEM_CONFIG_CHANGED_EVENT, alphasiftApi } from '../../api/alphasift';
import { useAuth } from '../../contexts/AuthContext';
import { useAgentChatStore } from '../../stores/agentChatStore';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiLanguage, UiTextKey } from '../../i18n/uiText';
import { cn } from '../../utils/cn';
import { ConfirmDialog } from '../common/ConfirmDialog';
import { StatusDot } from '../common/StatusDot';
import { UiLanguageToggle } from '../i18n/UiLanguageToggle';
import { ThemeToggle } from '../theme/ThemeToggle';
import { WorkspaceSwitcher } from './WorkspaceSwitcher';
import { centerFromPath, readRememberedCenter } from '../../utils/workspaceCenter';

type SidebarNavProps = {
  collapsed?: boolean;
  onNavigate?: () => void;
  variant?: 'default' | 'rail';
};

type NavItem = {
  key: string;
  labelKey?: UiTextKey;
  label?: Record<UiLanguage, string>;
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  exact?: boolean;
  badge?: 'completion';
};

const STOCK_NAV_ITEMS: NavItem[] = [
  { key: 'stock-home', label: { zh: '股票首页', en: 'Stock home' }, to: '/stocks', icon: Home, exact: true },
  { key: 'stock-chat', label: { zh: '问股票', en: 'Ask stocks' }, to: '/stocks/ask', icon: MessageSquareQuote, badge: 'completion' },
  { key: 'screening', label: { zh: '选股策略', en: 'Screening' }, to: '/stocks/screening', icon: Search },
  { key: 'stock-portfolio', label: { zh: '股票持仓', en: 'Stock holdings' }, to: '/stocks/portfolio', icon: BriefcaseBusiness },
  { key: 'stock-advice', label: { zh: '股票建议', en: 'Stock advice' }, to: '/stocks/advice', icon: Activity },
  { key: 'stock-backtest', label: { zh: '股票回测', en: 'Stock backtest' }, to: '/stocks/backtest', icon: BarChart3 },
  { key: 'stock-alerts', label: { zh: '股票告警', en: 'Stock alerts' }, to: '/stocks/alerts', icon: Bell },
];

const FUND_NAV_ITEMS: NavItem[] = [
  { key: 'fund-home', label: { zh: '基金首页', en: 'Fund home' }, to: '/funds', icon: Home, exact: true },
  { key: 'fund-chat', label: { zh: '问基金', en: 'Ask funds' }, to: '/funds/ask', icon: MessageSquareQuote },
  { key: 'fund-portfolio', label: { zh: '基金持仓', en: 'Fund holdings' }, to: '/funds/portfolio', icon: BriefcaseBusiness },
  { key: 'fund-compare', label: { zh: '基金对比', en: 'Fund compare' }, to: '/funds/compare', icon: GitCompareArrows },
  { key: 'fund-exposure', label: { zh: '行业穿透', en: 'Industry exposure' }, to: '/funds/industry-exposure', icon: Layers3 },
  { key: 'fund-cycle', label: { zh: '行业周期', en: 'Industry cycle' }, to: '/funds/industry-cycle', icon: TrendingUp },
  { key: 'fund-advice', label: { zh: '基金建议', en: 'Fund advice' }, to: '/funds/advice', icon: ShieldAlert },
];

const SHARED_NAV_ITEMS: NavItem[] = [
  { key: 'settings', labelKey: 'layout.nav.settings', to: '/settings', icon: Settings2 },
  { key: 'usage', labelKey: 'layout.nav.usage', to: '/usage', icon: Gauge },
  { key: 'users', label: { zh: '用户管理', en: 'Users' }, to: '/users', icon: UsersRound },
];

export const SidebarNav: React.FC<SidebarNavProps> = ({ collapsed = false, onNavigate, variant = 'default' }) => {
  const { authEnabled, logout } = useAuth();
  const location = useLocation();
  const { t, language } = useUiLanguage();
  const completionBadge = useAgentChatStore((state) => state.completionBadge);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [showAlphaSiftNav, setShowAlphaSiftNav] = useState(false);

  useEffect(() => {
    let active = true;

    const refreshAlphaSiftStatus = async () => {
      try {
        const status = await alphasiftApi.getStatus();
        if (active) {
          setShowAlphaSiftNav(status.enabled);
        }
      } catch {
        if (active) {
          setShowAlphaSiftNav(false);
        }
      }
    };

    void refreshAlphaSiftStatus();
    window.addEventListener(ALPHASIFT_CONFIG_CHANGED_EVENT, refreshAlphaSiftStatus);
    window.addEventListener(SYSTEM_CONFIG_CHANGED_EVENT, refreshAlphaSiftStatus);

    return () => {
      active = false;
      window.removeEventListener(ALPHASIFT_CONFIG_CHANGED_EVENT, refreshAlphaSiftStatus);
      window.removeEventListener(SYSTEM_CONFIG_CHANGED_EVENT, refreshAlphaSiftStatus);
    };
  }, []);

  const activeCenter = centerFromPath(location.pathname) ?? readRememberedCenter();
  const centerItems = activeCenter === 'funds' ? FUND_NAV_ITEMS : STOCK_NAV_ITEMS;
  const visibleCenterItems = showAlphaSiftNav ? centerItems : centerItems.filter((item) => item.key !== 'screening');
  const navItems = [...visibleCenterItems, ...SHARED_NAV_ITEMS];
  const isRail = variant === 'rail';
  const itemBaseClass = cn(
    'group relative flex h-[var(--nav-item-height)] w-full items-center overflow-hidden rounded-2xl border border-transparent text-sm leading-none text-secondary-text transition-all',
    isRail
      ? 'justify-center gap-2.5 px-2'
      : collapsed
        ? 'justify-center px-0'
        : 'gap-3 px-[var(--nav-item-padding-x)]'
  );
  const itemInteractiveClass = cn(
    itemBaseClass,
    'hover:bg-[var(--nav-hover-bg)] hover:text-foreground'
  );
  const itemActiveClass = 'border-[var(--nav-active-border)] bg-[var(--nav-active-bg)] font-medium text-[hsl(var(--primary))]';
  const itemIconClass = cn(isRail ? 'h-[18px] w-[18px]' : 'h-5 w-5', 'shrink-0');
  const itemLabelClass = cn('truncate', isRail ? 'text-center' : '');

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div
        className={cn(
          'flex items-center',
          isRail ? 'mb-5 justify-center gap-2 pt-1' : 'mb-4 gap-2 px-1',
          collapsed || isRail ? 'justify-center' : ''
        )}
      >
        <div
          className={cn(
            'flex items-center justify-center bg-primary-gradient text-[hsl(var(--primary-foreground))] shadow-[0_12px_28px_var(--nav-brand-shadow)]',
            isRail ? 'h-9 w-9 rounded-[1rem]' : 'h-10 w-10 rounded-2xl'
          )}
        >
          <BarChart3 className={cn(isRail ? 'h-[19px] w-[19px]' : 'h-5 w-5')} />
        </div>
        {!collapsed ? (
          <p className={cn('min-w-0 truncate font-semibold text-foreground', isRail ? 'text-[0.95rem] leading-none' : 'text-sm')}>DSA</p>
        ) : null}
      </div>

      <WorkspaceSwitcher compact={collapsed} onNavigate={onNavigate} />

      <nav className={cn('min-h-0 flex-1 overflow-y-auto overscroll-contain pr-0.5 [scrollbar-width:thin]', 'flex flex-col gap-1.5')} aria-label={t('layout.mainNav')}>
        {navItems.map(({ key, labelKey, label: literalLabel, to, icon: Icon, exact, badge }) => {
          const label = labelKey ? t(labelKey) : literalLabel?.[language] ?? key;
          return (
            <NavLink
              key={key}
              to={to}
              end={exact}
              onClick={onNavigate}
              aria-label={label}
              className={({ isActive }) =>
                cn(
                  itemInteractiveClass,
                  isActive ? itemActiveClass : ''
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={cn(itemIconClass, isActive ? 'text-[var(--nav-icon-active)]' : 'text-current')} />
                  {!collapsed ? <span className={itemLabelClass}>{label}</span> : null}
                  {badge === 'completion' && completionBadge ? (
                    <StatusDot
                      tone="info"
                      data-testid="chat-completion-badge"
                      className={cn(
                        'absolute right-3 border-2 border-background shadow-[0_0_10px_var(--nav-indicator-shadow)]',
                        collapsed ? 'right-2 top-2' : ''
                      )}
                      aria-label={t('layout.newChatMessage')}
                    />
                  ) : null}
                </>
              )}
            </NavLink>
          );
        })}

        <ThemeToggle
          variant={isRail ? 'rail' : 'nav'}
          collapsed={collapsed}
          wrapperClassName="w-full"
          triggerClassName={itemInteractiveClass}
          triggerActiveClassName={itemActiveClass}
          iconClassName={itemIconClass}
          labelClassName={itemLabelClass}
        />
        <UiLanguageToggle
          variant={isRail ? 'rail' : 'nav'}
          collapsed={collapsed}
          wrapperClassName="w-full"
          triggerClassName={itemInteractiveClass}
          triggerActiveClassName={itemActiveClass}
          iconClassName={itemIconClass}
          labelClassName={itemLabelClass}
        />
      </nav>

      {authEnabled ? (
        <button
          type="button"
          onClick={() => setShowLogoutConfirm(true)}
          className={cn(
            itemInteractiveClass,
            isRail ? 'mt-1.5' : 'mt-5'
          )}
        >
          <LogOut className={itemIconClass} />
          {!collapsed ? <span className={itemLabelClass}>{t('layout.logout')}</span> : null}
        </button>
      ) : null}

      <ConfirmDialog
        isOpen={showLogoutConfirm}
        title={t('layout.logoutTitle')}
        message={t('layout.logoutMessage')}
        confirmText={t('layout.logoutConfirm')}
        cancelText={t('common.cancel')}
        isDanger
        onConfirm={() => {
          setShowLogoutConfirm(false);
          onNavigate?.();
          void logout();
        }}
        onCancel={() => setShowLogoutConfirm(false)}
      />
    </div>
  );
};
