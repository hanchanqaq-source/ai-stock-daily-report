import type React from 'react';
import { lazy, useEffect } from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { ApiErrorAlert, Shell } from './components/common';
import {
  PageLoadingFallback,
  RouteOutletBoundary,
  StandaloneRouteBoundary,
} from './components/layout/RouteBoundary';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { PortfolioUserProvider } from './contexts/PortfolioUserContext';
import { UiLanguageProvider, useUiLanguage } from './contexts/UiLanguageContext';
import { useAgentChatStore } from './stores/agentChatStore';
import { readRememberedCenter } from './utils/workspaceCenter';
import './App.css';

const WorkspaceLandingPage = lazy(() => import('./pages/WorkspaceLandingPage'));
const HomePage = lazy(() => import('./pages/HomePage'));
const BacktestPage = lazy(() => import('./pages/BacktestPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));
const ChatPage = lazy(() => import('./pages/ChatPage'));
const PortfolioPage = lazy(() => import('./pages/PersonalPortfolioPage'));
const StockPortfolioManagementPage = lazy(() => import('./pages/StockPortfolioManagementPage'));
const UsersPage = lazy(() => import('./pages/UsersPage'));
const DecisionSignalsPage = lazy(() => import('./pages/DecisionSignalsPage'));
const AlertsPage = lazy(() => import('./pages/AlertsPage'));
const TokenUsagePage = lazy(() => import('./pages/TokenUsagePage'));
const StockScreeningPage = lazy(() => import('./pages/StockScreeningPage'));
const FundCenterPage = lazy(() => import('./pages/FundCenterPage'));

const LegacyRedirect: React.FC<{ to: string }> = ({ to }) => {
  const location = useLocation();
  return <Navigate to={`${to}${location.search}`} replace />;
};

const LegacyPortfolioRedirect: React.FC = () => (
  <LegacyRedirect to={readRememberedCenter() === 'funds' ? '/funds/portfolio' : '/stocks/portfolio'} />
);

const AppContent: React.FC = () => {
  const location = useLocation();
  const { authEnabled, loggedIn, isLoading, loadError, refreshStatus } = useAuth();
  const { t } = useUiLanguage();

  useEffect(() => {
    useAgentChatStore.getState().setCurrentRoute(location.pathname);
  }, [location.pathname]);

  if (isLoading) {
    return <PageLoadingFallback />;
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-base px-4">
        <div className="w-full max-w-lg">
          <ApiErrorAlert error={loadError} />
        </div>
        <button
          type="button"
          className="btn-primary"
          onClick={() => void refreshStatus()}
        >
          {t('common.retry')}
        </button>
      </div>
    );
  }

  if (authEnabled && !loggedIn) {
    if (location.pathname === '/login') {
      return (
        <StandaloneRouteBoundary>
          <LoginPage />
        </StandaloneRouteBoundary>
      );
    }
    const redirect = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }

  if (location.pathname === '/login') {
    return <Navigate to="/" replace />;
  }

  return (
    <Routes>
      <Route
        element={(
          <Shell>
            <RouteOutletBoundary />
          </Shell>
        )}
      >
        <Route path="/" element={<WorkspaceLandingPage />} />

        <Route path="/stocks" element={<HomePage />} />
        <Route path="/stocks/ask" element={<ChatPage />} />
        <Route path="/stocks/portfolio" element={<PortfolioPage domain="stock" />} />
        <Route path="/stocks/portfolio/manage" element={<StockPortfolioManagementPage />} />
        <Route path="/stocks/screening" element={<StockScreeningPage />} />
        <Route path="/stocks/advice" element={<DecisionSignalsPage />} />
        <Route path="/stocks/backtest" element={<BacktestPage />} />
        <Route path="/stocks/alerts" element={<AlertsPage />} />

        <Route path="/funds" element={<FundCenterPage section="home" />} />
        <Route path="/funds/ask" element={<FundCenterPage section="ask" />} />
        <Route path="/funds/portfolio" element={<PortfolioPage domain="fund" />} />
        <Route path="/funds/compare" element={<FundCenterPage section="compare" />} />
        <Route path="/funds/industry-exposure" element={<FundCenterPage section="industry-exposure" />} />
        <Route path="/funds/industry-cycle" element={<FundCenterPage section="industry-cycle" />} />
        <Route path="/funds/advice" element={<FundCenterPage section="advice" />} />

        <Route path="/chat" element={<LegacyRedirect to="/stocks/ask" />} />
        <Route path="/portfolio" element={<LegacyPortfolioRedirect />} />
        <Route path="/portfolio/stock-management" element={<LegacyRedirect to="/stocks/portfolio/manage" />} />
        <Route path="/decision-signals" element={<LegacyRedirect to="/stocks/advice" />} />
        <Route path="/screening" element={<LegacyRedirect to="/stocks/screening" />} />
        <Route path="/backtest" element={<LegacyRedirect to="/stocks/backtest" />} />
        <Route path="/alerts" element={<LegacyRedirect to="/stocks/alerts" />} />

        <Route path="/users" element={<UsersPage />} />
        <Route path="/usage" element={<TokenUsagePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
};

const App: React.FC = () => {
  return (
    <UiLanguageProvider>
      <PortfolioUserProvider>
        <Router>
          <AuthProvider>
            <AppContent />
          </AuthProvider>
        </Router>
      </PortfolioUserProvider>
    </UiLanguageProvider>
  );
};

export default App;
