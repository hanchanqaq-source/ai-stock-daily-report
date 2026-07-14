import { useState } from 'react';
import { Button } from '../components/common';

type SettingsTab = 'credentials' | 'sources' | 'connection';

const TABS: Array<{ id: SettingsTab; label: string; description: string }> = [
  { id: 'credentials', label: '接口与密钥', description: '展示后续接口配置入口，本阶段不保存真实密钥。' },
  { id: 'sources', label: '数据源管理', description: '展示公开只读行情与后续数据源的静态阶段状态。' },
  { id: 'connection', label: '连接测试', description: '预留连接测试入口，本阶段不发起真实请求。' },
];

const API_CARDS = [
  { name: 'AI 模型接口', status: '后续接入', description: '用于后续配置模型服务访问参数，本阶段仅展示占位状态。' },
  { name: '行情数据接口', status: '无需密钥', description: '用于后续统一管理行情数据源配置，本阶段不读取账户或凭证。' },
  { name: '通知接口', status: '未配置', description: '用于后续配置通知渠道，本阶段不保存 Token、Webhook 或其他敏感信息。' },
];

const OTHER_SOURCES = ['Longbridge', 'Tushare', '账户接口', '基金净值接口'];

function SkeletonNotice() {
  return (
    <div className="rounded-2xl border border-cyan/25 bg-cyan/8 px-4 py-3 text-sm leading-6 text-secondary-text">
      <span className="font-semibold text-foreground">App-M4.1 设置工作台骨架：</span>
      {' '}当前仅提供前端静态页面、导航和状态说明；不读取 .env，不保存真实密钥，不发起网络请求。
    </div>
  );
}

function InterfaceAndKeysTab() {
  return (
    <section className="space-y-4" aria-labelledby="settings-credentials-title">
      <div>
        <h2 id="settings-credentials-title" className="text-lg font-semibold text-foreground">接口与密钥</h2>
        <p className="mt-1 text-sm leading-6 text-secondary-text">这些配置入口将在后续阶段接入。本阶段所有操作控件均禁用。</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {API_CARDS.map((card) => (
          <article key={card.name} className="rounded-[1.35rem] border settings-border bg-card/94 p-5 shadow-soft-card-strong">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h3 className="text-base font-semibold text-foreground">{card.name}</h3>
              <span className="rounded-full border settings-border bg-background/60 px-3 py-1 text-xs font-medium text-muted-text">{card.status}</span>
            </div>
            <p className="mt-3 min-h-12 text-sm leading-6 text-secondary-text">{card.description}</p>
            <label className="mt-4 block text-xs font-medium text-muted-text" htmlFor={`disabled-${card.name}`}>配置输入</label>
            <input
              id={`disabled-${card.name}`}
              className="mt-2 w-full rounded-2xl border settings-border bg-background/45 px-3 py-2 text-sm text-muted-text"
              value="App-M4.1 暂不保存真实密钥"
              disabled
              readOnly
            />
            <Button type="button" variant="settings-secondary" className="mt-4 w-full justify-center" disabled>
              配置（App-M4.1 暂不可用）
            </Button>
          </article>
        ))}
      </div>
    </section>
  );
}

function DataSourcesTab() {
  return (
    <section className="space-y-4" aria-labelledby="settings-sources-title">
      <div>
        <h2 id="settings-sources-title" className="text-lg font-semibold text-foreground">数据源管理</h2>
        <p className="mt-1 text-sm leading-6 text-secondary-text">仅展示静态阶段状态，不初始化 Provider、不检查凭证、不连接账户。</p>
      </div>
      <article className="rounded-[1.35rem] border settings-border bg-card/94 p-5 shadow-soft-card-strong">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-base font-semibold text-foreground">AkShare 公开 A 股行情</h3>
          <span className="rounded-full border border-slate-300/40 bg-background/60 px-3 py-1 text-xs font-semibold text-muted-text">默认状态：关闭</span>
        </div>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          {[
            ['类型', '公开只读行情'],
            ['当前阶段', '已具备手动 dry-run 基础'],
            ['正式页面接入', '尚未启用'],
            ['账户读取', '无账户读取'],
            ['交易权限', '无交易权限'],
            ['密钥要求', '无密钥要求'],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border settings-border bg-background/35 px-4 py-3">
              <dt className="text-xs text-muted-text">{label}</dt>
              <dd className="mt-1 font-medium text-foreground">{value}</dd>
            </div>
          ))}
        </dl>
      </article>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {OTHER_SOURCES.map((source) => (
          <article key={source} className="rounded-[1.25rem] border settings-border bg-card/80 p-4 shadow-soft-card">
            <h3 className="font-semibold text-foreground">{source}</h3>
            <p className="mt-2 text-sm text-muted-text">状态：后续接入</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function ConnectionTestTab() {
  const [message, setMessage] = useState('等待后续阶段启用。');

  return (
    <section className="space-y-4" aria-labelledby="settings-connection-title">
      <div>
        <h2 id="settings-connection-title" className="text-lg font-semibold text-foreground">连接测试</h2>
        <p className="mt-1 text-sm leading-6 text-secondary-text">本阶段只提供界面骨架，不展示成功态、延迟数值或实时可用状态。</p>
      </div>
      <div className="rounded-[1.35rem] border settings-border bg-card/94 p-5 shadow-soft-card-strong">
        <label htmlFor="connection-source" className="text-sm font-medium text-foreground">数据源选择区域</label>
        <select id="connection-source" className="mt-2 w-full rounded-2xl border settings-border bg-background/45 px-3 py-2 text-sm text-muted-text" disabled defaultValue="akshare">
          <option value="akshare">AkShare 公开 A 股行情（未启用测试）</option>
        </select>
        <div className="mt-4 rounded-2xl border settings-border bg-background/35 px-4 py-3">
          <p className="text-xs text-muted-text">当前状态区域</p>
          <p className="mt-1 text-sm font-medium text-foreground">{message}</p>
        </div>
        <Button type="button" variant="settings-secondary" className="mt-4" onClick={() => setMessage('App-M4.1 尚未启用真实连接测试。')}>
          开始连接测试
        </Button>
      </div>
    </section>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('credentials');
  const active = TABS.find((tab) => tab.id === activeTab) ?? TABS[0];

  return (
    <div className="settings-page min-h-full px-4 pb-6 pt-4 md:px-6">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5">
        <header className="rounded-[1.5rem] border settings-border bg-card/94 px-5 py-5 shadow-soft-card-strong backdrop-blur-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan">Settings Workspace</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">设置工作台</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-secondary-text">为接口配置、数据源管理和连接测试预留的正式工作台骨架。当前阶段仅包含静态状态与禁用能力说明。</p>
        </header>

        <SkeletonNotice />

        <div className="rounded-[1.5rem] border settings-border bg-card/90 p-2 shadow-soft-card">
          <div className="grid gap-2 md:grid-cols-3" role="tablist" aria-label="设置工作台页签">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                className={`rounded-2xl px-4 py-3 text-left transition ${activeTab === tab.id ? 'bg-primary-gradient text-[hsl(var(--primary-foreground))] shadow-glow-cyan' : 'text-secondary-text hover:bg-[var(--settings-surface-hover)] hover:text-foreground'}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span className="block text-sm font-semibold">{tab.label}</span>
                <span className="mt-1 block text-xs opacity-85">{tab.description}</span>
              </button>
            ))}
          </div>
        </div>

        <main className="rounded-[1.5rem] border settings-border bg-card/90 p-5 shadow-soft-card-strong" aria-label={active.label}>
          {activeTab === 'credentials' ? <InterfaceAndKeysTab /> : null}
          {activeTab === 'sources' ? <DataSourcesTab /> : null}
          {activeTab === 'connection' ? <ConnectionTestTab /> : null}
        </main>
      </div>
    </div>
  );
}
