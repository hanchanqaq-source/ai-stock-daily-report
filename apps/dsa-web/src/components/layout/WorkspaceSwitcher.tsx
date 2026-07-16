import type React from 'react';
import { Landmark, LineChart, UserRound } from 'lucide-react';
import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { usePortfolioUsers } from '../../contexts/PortfolioUserContext';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { centerFromPath, readRememberedCenter, rememberCenter, type WorkspaceCenter } from '../../utils/workspaceCenter';
import { cn } from '../../utils/cn';

type WorkspaceSwitcherProps = {
  compact?: boolean;
  onNavigate?: () => void;
};

const LABELS = {
  zh: {
    switcher: '业务中心', stocks: '股票中心', funds: '基金中心', currentUser: '当前用户', manageUsers: '管理用户',
  },
  en: {
    switcher: 'Workspace', stocks: 'Stocks', funds: 'Funds', currentUser: 'Current user', manageUsers: 'Manage users',
  },
} as const;

export const WorkspaceSwitcher: React.FC<WorkspaceSwitcherProps> = ({ compact = false, onNavigate }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { language } = useUiLanguage();
  const { users, activeUserId, setActiveUserId } = usePortfolioUsers();
  const text = LABELS[language];
  const routeCenter = centerFromPath(location.pathname);
  const activeCenter = routeCenter ?? readRememberedCenter();

  useEffect(() => {
    if (routeCenter) rememberCenter(routeCenter);
  }, [routeCenter]);

  const openCenter = (center: WorkspaceCenter) => {
    rememberCenter(center);
    navigate(center === 'stocks' ? '/stocks' : '/funds');
    onNavigate?.();
  };

  return (
    <section className="mb-3 space-y-2" aria-label={text.switcher} data-testid="workspace-switcher">
      <div className="grid grid-cols-2 gap-1 rounded-xl border border-border/70 bg-background/35 p-1">
        {([
          ['stocks', text.stocks, LineChart],
          ['funds', text.funds, Landmark],
        ] as const).map(([center, label, Icon]) => (
          <button
            key={center}
            type="button"
            className={cn(
              'flex min-w-0 items-center justify-center rounded-lg px-1.5 py-2 text-[11px] transition-colors',
              activeCenter === center
                ? 'bg-primary text-[hsl(var(--primary-foreground))]'
                : 'text-secondary-text hover:bg-hover hover:text-foreground',
            )}
            aria-pressed={activeCenter === center}
            aria-label={label}
            onClick={() => openCenter(center)}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {!compact ? <span className="ml-1 truncate">{label}</span> : null}
          </button>
        ))}
      </div>

      <label className="block space-y-1 text-[10px] text-secondary-text">
        <span className="flex items-center gap-1 px-1"><UserRound className="h-3 w-3" />{text.currentUser}</span>
        <select
          className="input-surface input-focus-glow h-8 w-full rounded-lg border bg-transparent px-2 text-xs text-foreground"
          value={activeUserId}
          aria-label={text.currentUser}
          onChange={(event) => setActiveUserId(event.target.value)}
        >
          {users.map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}
        </select>
      </label>
      {!compact ? (
        <button type="button" className="w-full text-center text-[10px] text-secondary-text hover:text-foreground" onClick={() => { navigate('/users'); onNavigate?.(); }}>
          {text.manageUsers}
        </button>
      ) : null}
    </section>
  );
};
