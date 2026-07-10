const fallbackPayload = {
  account_id: "demo_account",
  account_name: "示例账户",
  payload_status: "safe_for_account_page",
  display_mode: "redacted",
  data_mode: "dry_run",
  can_write_to_public_repo: false,
  sections: {
    stock_etf: { enabled: true, title: "股票 / ETF 行情", display_models: [] },
    fund_nav: { enabled: true, title: "场外基金净值", display_models: [] },
    observation_points: {
      enabled: true,
      title: "个人观察点位",
      items: [
        { id: "demo_observation_buy_001", label: "买入观察", category: "buy_watch", asset_name: "示例股票A", asset_code: "000000", asset_type: "stock", market: "CN", point_display: "<redacted>", status: "watching", risk_level: "medium", text: "仅作为个人观察记录，不自动下单。", disclaimer: "不构成强制交易指令。" },
        { id: "demo_observation_add_001", label: "加仓观察", category: "add_watch", asset_name: "示例ETF A", asset_code: "demo_etf_001", asset_type: "etf", market: "CN", point_display: "<redacted>", status: "waiting", risk_level: "medium", text: "等待回调确认后再记录。", disclaimer: "不构成强制交易指令。" },
        { id: "demo_observation_profit_001", label: "止盈观察", category: "take_profit_watch", asset_name: "示例场外基金A", asset_code: "000001", asset_type: "fund", market: "CN", point_display: "<redacted>", status: "watching", risk_level: "low", text: "接近目标区时重点观察。", disclaimer: "不构成强制交易指令。" },
        { id: "demo_observation_risk_001", label: "风险位", category: "risk_watch", asset_name: "示例股票A", asset_code: "000000", asset_type: "stock", market: "CN", point_display: "<redacted>", status: "risk_watch", risk_level: "high", text: "跌破关键位置时提高风险等级，仅作为个人观察记录。", disclaimer: "不构成强制交易指令。" }
      ]
    }
  },
  dashboard_summary: {
    title: "账户首页综合看板",
    account_status: "本地安全预览",
    data_status: "dry_run",
    display_status: "redacted",
    counts: { stock_etf: 0, fund_nav: 0, observation_points: 4, blocked: 0, unavailable: 0, redacted: 4 },
    quick_notes: ["当前页面为本地安全预览。", "默认展示脱敏结果。", "不保存原始 provider 数据。"]
  },
  safety_badges: ["已审计", "默认脱敏", "禁止写入真实数据", "不自动下单", "不构成强制交易指令"],
  warnings: [
    "本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。",
    "盘中估算仅供观察，最终以基金公司公布净值为准。"
  ],
  market_indices: buildFallbackMarketIndices(),
  disclaimer: "本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。"
};

function getFallbackPayload() { return fallbackPayload; }
function byId(id) { return document.getElementById(id); }
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  }[char]));
}
function setSafeHtml(id, html) { const node = byId(id); if (node) node.innerHTML = html; }

async function loadFinalPagePayload() {
  try {
    const response = await fetch("demo_final_page_payload.json");
    if (!response.ok) throw new Error("Cannot load local demo payload");
    return await response.json();
  } catch (error) { return fallbackPayload; }
}

function formatDisplayValue(value) {
  if (value === undefined || value === null || value === "") return "未提供";
  return value;
}
function renderRedactedValue(value) {
  const text = value === "<redacted>" ? "<redacted>" : formatDisplayValue(value);
  const className = text === "<redacted>" ? "redacted-value" : "";
  return `<span class="${className}">${escapeHtml(text)}</span>`;
}
function renderAssetBadges(badges = []) {
  if (!Array.isArray(badges) || !badges.length) return '<span class="badge muted">未提供 badge</span>';
  return badges.map((text) => `<span class="badge">${escapeHtml(text)}</span>`).join("");
}
function renderDataStatusBadge(model = {}) {
  const status = model.source_status || model.display_status || "未提供";
  return `<span class="badge data-status">${escapeHtml(status)}</span>`;
}
function renderMetaRows(model = {}) {
  const rows = [
    ["provider", model.provider], ["source_status", model.source_status],
    ["checked_at", model.checked_at], ["display_mode", model.display_mode]
  ];
  return rows.map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(formatDisplayValue(value))}</dd>`).join("");
}
function renderAssetHeader(model = {}) {
  return `<div class="asset-card-header"><div><strong>${escapeHtml(formatDisplayValue(model.name))}</strong><span>${escapeHtml(formatDisplayValue(model.code))} · ${escapeHtml(formatDisplayValue(model.market))} · ${escapeHtml(formatDisplayValue(model.type))}</span></div>${renderDataStatusBadge(model)}</div>`;
}
function renderBlockedCard(model = {}, type = "asset") {
  return `<article class="asset-card blocked-card">${renderAssetHeader(model)}<p class="blocked-message">数据已被安全闸门拦截，不显示原始行情数据。</p><dl>${renderMetaRows(model)}</dl><div class="badge-row compact">${renderAssetBadges(model.badges)}</div></article>`;
}
function renderUnavailableCard(model = {}, type = "asset") {
  const message = type === "fund" ? "当前场外基金净值不可用。" : "当前行情不可用。";
  return `<article class="asset-card unavailable-card">${renderAssetHeader(model)}<p class="unavailable-message">${escapeHtml(message)}</p><dl>${renderMetaRows(model)}</dl><div class="badge-row compact">${renderAssetBadges(model.badges)}</div>${type === "fund" ? '<p class="section-note">盘中估算仅供观察，最终以基金公司公布净值为准。</p>' : ''}</article>`;
}
function renderStockEtfCards(section = {}) {
  if (section.enabled === false) return '<p class="empty-state">股票 / ETF 区域暂未启用</p>';
  const models = Array.isArray(section.display_models) ? section.display_models : [];
  if (!models.length) return '<p class="empty-state">股票 / ETF 区域暂无可展示项目</p>';
  return models.map((model = {}) => {
    if (model.display_status === "blocked") return renderBlockedCard(model, "stock");
    if (model.display_status === "unavailable") return renderUnavailableCard(model, "stock");
    const quote = model.quote_display || {};
    const redact = model.display_mode === "redacted";
    const val = (v) => renderRedactedValue(redact ? "<redacted>" : v);
    return `<article class="asset-card stock-card">${renderAssetHeader(model)}<dl><dt>最新价</dt><dd>${val(quote.last_price)}</dd><dt>涨跌幅</dt><dd>${val(quote.change_pct)}</dd><dt>成交额</dt><dd>${val(quote.turnover)}</dd>${renderMetaRows(model)}</dl><div class="badge-row compact">${renderAssetBadges(model.badges)}</div></article>`;
  }).join("");
}
function renderStockEtfSection(section) {
  return renderStockEtfCards(section);
}

function renderFundNavCards(section = {}) {
  const note = '<p class="section-note">盘中估算仅供观察，最终以基金公司公布净值为准。</p>';
  if (section.enabled === false) return '<p class="empty-state">场外基金净值区域暂未启用</p>' + note;
  const models = Array.isArray(section.display_models) ? section.display_models : [];
  if (!models.length) return '<p class="empty-state">场外基金净值区域暂无可展示项目</p>' + note;
  return models.map((model = {}) => {
    if (model.display_status === "blocked") return renderBlockedCard(model, "fund") + note;
    if (model.display_status === "unavailable") return renderUnavailableCard(model, "fund");
    const nav = model.nav_display || {}, estimate = model.estimate_display || {};
    const redact = model.display_mode === "redacted";
    const val = (v) => renderRedactedValue(redact ? "<redacted>" : v);
    return `<article class="asset-card fund-card">${renderAssetHeader(model)}<dl><dt>单位净值</dt><dd>${val(nav.unit_nav)}</dd><dt>累计净值</dt><dd>${val(nav.accumulated_nav)}</dd><dt>日涨跌幅</dt><dd>${val(nav.daily_change_pct)}</dd><dt>净值日期</dt><dd>${escapeHtml(formatDisplayValue(nav.nav_date))}</dd><dt>估算净值</dt><dd>${val(estimate.estimated_nav)}</dd><dt>估算涨跌</dt><dd>${val(estimate.estimated_change_pct)}</dd><dt>估算更新时间</dt><dd>${escapeHtml(formatDisplayValue(estimate.estimate_time))}</dd>${renderMetaRows(model)}</dl>${note}<div class="badge-row compact">${renderAssetBadges(model.badges)}</div></article>`;
  }).join("");
}
function renderFundNavSection(section) {
  return renderFundNavCards(section);
}

function renderMarketDashboard(payload) {
  const sections = payload?.sections || {};
  setSafeHtml("stock-etf-section", renderStockEtfCards(sections.stock_etf || {}));
  setSafeHtml("fund-nav-section", renderFundNavCards(sections.fund_nav || {}));
}


function getSectionDisplayModels(payload, key) {
  const models = payload?.sections?.[key]?.display_models;
  return Array.isArray(models) ? models : [];
}
function countDisplayModelsByStatus(payload) {
  const models = [...getSectionDisplayModels(payload, "stock_etf"), ...getSectionDisplayModels(payload, "fund_nav")];
  return models.reduce((counts, model = {}) => {
    const status = model.display_status || model.source_status || "unavailable";
    counts[status] = (counts[status] || 0) + 1;
    if (model.display_mode === "redacted") counts.redacted = (counts.redacted || 0) + 1;
    return counts;
  }, { blocked: 0, unavailable: 0, redacted: 0 });
}
function countObservationPoints(payload) {
  const items = payload?.sections?.observation_points?.items;
  return Array.isArray(items) ? items.length : 0;
}
function buildDashboardSummaryFromPayload(payload = {}) {
  const statusCounts = countDisplayModelsByStatus(payload);
  const summary = payload.dashboard_summary || {};
  const counts = summary.counts || {};
  return {
    title: summary.title || "账户首页综合看板",
    account_status: summary.account_status || payload.payload_status || "unknown",
    data_status: summary.data_status || payload.data_mode || "unknown",
    display_status: summary.display_status || payload.display_mode || "unknown",
    counts: {
      stock_etf: counts.stock_etf ?? getSectionDisplayModels(payload, "stock_etf").length,
      fund_nav: counts.fund_nav ?? getSectionDisplayModels(payload, "fund_nav").length,
      observation_points: counts.observation_points ?? countObservationPoints(payload),
      blocked: counts.blocked ?? statusCounts.blocked ?? 0,
      unavailable: counts.unavailable ?? statusCounts.unavailable ?? 0,
      redacted: counts.redacted ?? statusCounts.redacted ?? 0
    },
    quick_notes: Array.isArray(summary.quick_notes) ? summary.quick_notes : ["当前页面为本地安全预览。", "默认展示脱敏结果。", "不保存原始 provider 数据。"]
  };
}
function renderQuickLink(label, targetId) {
  return `<a class="quick-link" href="#${escapeHtml(targetId)}">${escapeHtml(label)}</a>`;
}
function renderEmptyDashboardState(reason) {
  return `<p class="empty-state">${escapeHtml(reason || "暂无综合看板数据。")}</p>`;
}
function renderDashboardSummary(payload) {
  const summary = buildDashboardSummaryFromPayload(payload);
  const notes = summary.quick_notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("");
  const canWrite = payload?.can_write_to_public_repo === true ? "true" : "false";
  return `<div class="dashboard-hero"><div><p class="card-label">账户首页</p><h2>${escapeHtml(summary.title)}</h2><p class="dashboard-subtitle">账户名称：${escapeHtml(formatDisplayValue(payload?.account_name))}</p></div><dl class="dashboard-overview"><dt>payload_status</dt><dd>${escapeHtml(formatDisplayValue(payload?.payload_status))}</dd><dt>display_mode</dt><dd>${escapeHtml(formatDisplayValue(payload?.display_mode))}</dd><dt>data_mode</dt><dd>${escapeHtml(formatDisplayValue(payload?.data_mode))}</dd><dt>是否可写入仓库</dt><dd>${escapeHtml(canWrite)}</dd><dt>数据安全状态</dt><dd>${escapeHtml(summary.account_status)}</dd></dl><div class="quick-links">${renderQuickLink("股票 / ETF 行情", "holdings")}${renderQuickLink("场外基金净值", "fund-nav")}${renderQuickLink("个人观察点位", "points")}${renderQuickLink("风险提醒", "risk-warnings")}</div><ul class="dashboard-notes">${notes}</ul></div>`;
}
function renderDashboardMetricCards(payload) {
  const counts = buildDashboardSummaryFromPayload(payload).counts;
  const metrics = [["股票 / ETF 数量", counts.stock_etf], ["场外基金数量", counts.fund_nav], ["个人观察点位数量", counts.observation_points], ["blocked 数量", counts.blocked], ["unavailable 数量", counts.unavailable], ["redacted 数量", counts.redacted]];
  return metrics.map(([label, value]) => `<article class="metric-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`).join("");
}
function renderDashboardSafetyPanel(payload) {
  const badges = [...(Array.isArray(payload?.safety_badges) ? payload.safety_badges : []), "不自动下单", "不构成强制交易指令"];
  return `<div class="safety-panel"><h3>数据安全状态</h3><div class="badge-row">${renderAssetBadges([...new Set(badges)])}</div><p>本地预览禁止写入未脱敏数据，不保存原始 provider 数据、个人敏感字段或密钥字段。</p></div>`;
}

function buildFallbackMarketIndices() {
  const makeItem = (name, code, indicatorType = "official_index") => ({
    name,
    code,
    display_change_pct: "<redacted>",
    display_status: "redacted",
    indicator_type: indicatorType,
    note: indicatorType === "official_index" ? "示例官方指数，不是真实行情。" : "系统计算指标，非官方指数。"
  });
  return {
    data_mode: "dry_run",
    display_mode: "redacted",
    source_status: "demo_only",
    can_write_to_public_repo: false,
    markets: {
      global: {
        label: "全球总览",
        summary: "示例：全球市场指数模块仅展示脱敏 demo，不代表真实行情。",
        groups: [
          { group_key: "cn_summary", group_label: "A股摘要", items: [makeItem("A股指数矩阵摘要", "DEMO_GLOBAL_CN", "demo_only")] },
          { group_key: "hk_summary", group_label: "港股摘要", items: [makeItem("港股指数矩阵摘要", "DEMO_GLOBAL_HK", "demo_only")] },
          { group_key: "us_summary", group_label: "美股摘要", items: [makeItem("美股指数矩阵摘要", "DEMO_GLOBAL_US", "demo_only")] },
          { group_key: "kr_summary", group_label: "韩股摘要", items: [makeItem("韩股指数矩阵摘要", "DEMO_GLOBAL_KR", "demo_only")] },
          { group_key: "global_risk", group_label: "全球风险提示", items: [makeItem("跨市场风险提示", "DEMO_GLOBAL_RISK", "demo_only")] },
          { group_key: "data_note", group_label: "数据说明", items: [makeItem("数据说明", "DEMO_GLOBAL_NOTE", "demo_only")] }
        ]
      },
      cn: { label: "A股", summary: "示例：A股指数矩阵包含权重核心、中小盘、成长科技和体感指标。", groups: [
        { group_key: "core_weight", group_label: "权重核心", items: ["上证指数", "深证成指", "沪深300", "中证A500", "上证50"].map((name, index) => makeItem(name, `DEMO_CN_${index}`)) },
        { group_key: "small_mid", group_label: "中小盘", items: ["中证500", "中证1000", "中证2000 / 国证2000"].map((name, index) => makeItem(name, `DEMO_CN_SM_${index}`)) },
        { group_key: "growth_tech", group_label: "成长科技", items: ["创业板指", "创业板50", "科创50", "科创100", "北证50"].map((name, index) => makeItem(name, `DEMO_CN_GT_${index}`)) },
        { group_key: "market_feel", group_label: "市场体感", items: ["A股中位数涨跌幅", "A股上涨家数占比", "A股涨跌停差", "A股成交额", "全A等权涨跌"].map((name, index) => makeItem(name, `DEMO_CN_FEEL_${index}`, "computed_breadth_indicator")) }
      ] },
      hk: { label: "港股", summary: "示例：港股指数矩阵包含权重核心、内地权重、科技成长和市场体感。", groups: [
        { group_key: "core_weight", group_label: "权重核心", items: ["恒生指数", "恒生综合指数"].map((name, index) => makeItem(name, `DEMO_HK_${index}`)) },
        { group_key: "mainland_weight", group_label: "内地权重", items: [makeItem("恒生中国企业指数 / 国企指数", "DEMO_HK_HSCEI")] },
        { group_key: "growth_tech", group_label: "科技成长", items: [makeItem("恒生科技指数", "DEMO_HK_HSTECH")] },
        { group_key: "market_feel", group_label: "市场体感", items: ["港股中位数涨跌", "港股上涨家数占比", "港股成交额"].map((name, index) => makeItem(name, `DEMO_HK_FEEL_${index}`, "computed_breadth_indicator")) }
      ] },
      us: { label: "美股", summary: "示例：美股指数矩阵包含权重核心、科技成长、中小盘和市场广度 / 体感。", groups: [
        { group_key: "core_weight", group_label: "权重核心", items: ["标普500", "道琼斯", "纳斯达克综合"].map((name, index) => makeItem(name, `DEMO_US_${index}`)) },
        { group_key: "growth_tech", group_label: "科技成长", items: ["纳斯达克100", "费城半导体指数"].map((name, index) => makeItem(name, `DEMO_US_GT_${index}`)) },
        { group_key: "small_mid", group_label: "中小盘", items: ["罗素2000", "标普400", "标普600"].map((name, index) => makeItem(name, `DEMO_US_SM_${index}`)) },
        { group_key: "breadth_feel", group_label: "市场广度 / 体感", items: ["标普500等权", "NYSE上涨家数占比", "Nasdaq上涨家数占比", "美股中位数涨跌"].map((name, index) => makeItem(name, `DEMO_US_FEEL_${index}`, "computed_breadth_indicator")) }
      ] },
      kr: { label: "韩股", summary: "示例：韩股指数矩阵包含权重核心、成长科技、综合指数和市场体感。", groups: [
        { group_key: "core_weight", group_label: "权重核心", items: ["KOSPI", "KOSPI 200"].map((name, index) => makeItem(name, `DEMO_KR_${index}`)) },
        { group_key: "growth_tech", group_label: "成长科技", items: ["KOSDAQ", "KOSDAQ 150"].map((name, index) => makeItem(name, `DEMO_KR_GT_${index}`)) },
        { group_key: "composite", group_label: "综合指数", items: [makeItem("KRX 300", "DEMO_KR_KRX300")] },
        { group_key: "market_feel", group_label: "市场体感", items: ["韩股中位数涨跌", "韩股上涨家数占比", "韩股成交额"].map((name, index) => makeItem(name, `DEMO_KR_FEEL_${index}`, "computed_breadth_indicator")) }
      ] }
    },
    disclaimer: "本模块当前仅为本地 demo 展示，不请求真实行情，不保存未脱敏价格或涨跌幅；系统计算指标，非官方指数。"
  };
}
function getMarketIndicesFromPayload(payload) {
  const source = payload?.market_indices;
  if (!source || typeof source !== "object") return buildFallbackMarketIndices();
  return { ...buildFallbackMarketIndices(), ...source, markets: source.markets || buildFallbackMarketIndices().markets };
}
function normalizeMarketIndexLabel(marketKey, marketData = {}) {
  const fallbackLabels = { global: "全球总览", cn: "A股", hk: "港股", us: "美股", kr: "韩股" };
  return marketData.label || fallbackLabels[marketKey] || marketKey;
}
function renderIndicatorTypeBadge(indicatorType) {
  const labels = {
    official_index: "官方指数",
    computed_breadth_indicator: "系统计算指标",
    computed_sentiment_indicator: "系统计算指标",
    demo_only: "Demo"
  };
  const label = labels[indicatorType] || "Demo";
  return `<span class="indicator-type-badge indicator-${escapeHtml(indicatorType || "demo_only")}">${escapeHtml(label)}</span>`;
}
function renderMarketIndexItem(item = {}) {
  const indicatorType = item.indicator_type || "demo_only";
  const note = indicatorType.startsWith("computed") ? "系统计算指标，非官方指数。" : item.note;
  return `<article class="market-index-card">
    <div class="market-index-card-header"><strong>${escapeHtml(formatDisplayValue(item.name))}</strong>${renderIndicatorTypeBadge(indicatorType)}</div>
    <dl><dt>代码</dt><dd>${escapeHtml(formatDisplayValue(item.code))}</dd><dt>涨跌幅</dt><dd>${renderRedactedValue(item.display_change_pct || "<redacted>")}</dd><dt>状态</dt><dd>${escapeHtml(formatDisplayValue(item.display_status || "redacted"))}</dd></dl>
    <p>${escapeHtml(formatDisplayValue(note || "示例数据，不是真实行情。"))}</p>
  </article>`;
}
function renderMarketIndexGroup(group = {}) {
  const items = Array.isArray(group.items) ? group.items : [];
  return `<section class="market-index-group">
    <h3>${escapeHtml(formatDisplayValue(group.group_label))}</h3>
    <div class="market-index-card-grid">${items.map((item) => renderMarketIndexItem(item)).join("") || '<p class="empty-state">暂无指数项目。</p>'}</div>
  </section>`;
}
function renderMarketIndexPanel(marketKey, marketData = {}) {
  const groups = Array.isArray(marketData.groups) ? marketData.groups : [];
  return `<div class="market-index-panel-inner" data-market="${escapeHtml(marketKey)}">
    <p class="card-label">${escapeHtml(normalizeMarketIndexLabel(marketKey, marketData))}</p>
    <h3>${escapeHtml(normalizeMarketIndexLabel(marketKey, marketData))}指数矩阵</h3>
    <p class="section-note">${escapeHtml(formatDisplayValue(marketData.summary))}</p>
    ${groups.map((group) => renderMarketIndexGroup(group)).join("") || '<p class="empty-state">暂无指数矩阵。</p>'}
  </div>`;
}
function setActiveMarketIndexTab(marketKey) {
  document.querySelectorAll(".market-index-tab").forEach((tab) => {
    const active = tab.getAttribute("data-market") === marketKey;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", active ? "true" : "false");
  });
  document.querySelectorAll(".market-index-panel").forEach((panel) => {
    panel.hidden = panel.id !== `market-index-${marketKey === "global" ? "overview" : marketKey}`;
  });
}
function renderMarketIndexTabs(markets = {}) {
  const order = ["global", "cn", "hk", "us", "kr"];
  return order.map((marketKey) => `<button class="market-index-tab${marketKey === "global" ? " active" : ""}" type="button" role="tab" aria-selected="${marketKey === "global" ? "true" : "false"}" data-market="${escapeHtml(marketKey)}">${escapeHtml(normalizeMarketIndexLabel(marketKey, markets[marketKey]))}</button>`).join("");
}
function renderMarketIndicesDashboard(payload) {
  const marketIndices = getMarketIndicesFromPayload(payload);
  const markets = marketIndices.markets || {};
  setSafeHtml("market-indices-tabs", renderMarketIndexTabs(markets));
  ["global", "cn", "hk", "us", "kr"].forEach((marketKey) => {
    const panelId = marketKey === "global" ? "market-index-overview" : `market-index-${marketKey}`;
    setSafeHtml(panelId, renderMarketIndexPanel(marketKey, markets[marketKey] || {}));
  });
  setSafeHtml("market-index-disclaimer", escapeHtml(marketIndices.disclaimer || "本模块当前仅为本地 demo 展示，不请求真实行情，不保存未脱敏价格或涨跌幅。"));
  const tabs = byId("market-indices-tabs");
  if (tabs) {
    tabs.querySelectorAll(".market-index-tab").forEach((tab) => {
      tab.addEventListener("click", () => setActiveMarketIndexTab(tab.getAttribute("data-market") || "global"));
    });
  }
  setActiveMarketIndexTab("global");
}
function renderDashboardQuickSections(payload) {
  const sections = payload?.sections || {};
  setSafeHtml("dashboard-quick-stock-etf", renderStockEtfCards({ ...sections.stock_etf, display_models: getSectionDisplayModels(payload, "stock_etf").slice(0, 3) }));
  setSafeHtml("dashboard-quick-fund-nav", renderFundNavCards({ ...sections.fund_nav, display_models: getSectionDisplayModels(payload, "fund_nav").slice(0, 3) }));
  const points = payload?.sections?.observation_points?.items;
  setSafeHtml("dashboard-quick-observation-points", renderObservationPointCards(Array.isArray(points) ? points.slice(0, 4) : []));
}
function renderDashboardWarnings(payload) {
  const warnings = Array.isArray(payload?.warnings) && payload.warnings.length ? payload.warnings : ["暂无额外风险提示。"];
  return `<ul>${warnings.map((text) => `<li>${escapeHtml(text)}</li>`).join("")}</ul>`;
}
function renderAccountHomeDashboard(payload) {
  if (!payload) { setSafeHtml("dashboard-summary", renderEmptyDashboardState("无法读取综合看板 payload。")); return; }
  setSafeHtml("dashboard-summary", renderDashboardSummary(payload));
  setSafeHtml("dashboard-metrics", renderDashboardMetricCards(payload));
  setSafeHtml("dashboard-safety-panel", renderDashboardSafetyPanel(payload));
  renderDashboardQuickSections(payload);
  setSafeHtml("dashboard-warnings", renderDashboardWarnings(payload));
}

function renderFinalPagePayload(payload) {
  const safePayload = payload || getFallbackPayload();
  renderAccountHomeDashboard(safePayload); renderAccountHeader(safePayload); renderSafetyBadges(safePayload); renderBlockedPayload(safePayload);
  renderMarketIndicesDashboard(safePayload);
  if (safePayload.payload_status === "blocked") {
    setSafeHtml("stock-etf-section", '<p class="empty-state">安全拦截状态下不显示股票 / ETF 真实值</p>');
    setSafeHtml("fund-nav-section", '<p class="empty-state">安全拦截状态下不显示场外基金净值真实值</p><p class="section-note">盘中估算仅供观察，最终以基金公司公布净值为准。</p>');
    setSafeHtml("observation-points-section", '<p class="empty-state">安全拦截状态下不显示上游原始内容</p>');
  } else { renderMarketDashboard(safePayload); renderObservationPoints(safePayload.sections?.observation_points); }
  renderWarnings(safePayload); renderDisclaimer(safePayload);
}
function renderAccountHeader(payload) {
  const name = byId("account-name"); if (name) name.textContent = payload.account_name || "示例账户";
  const status = byId("payload-status"); if (status) status.textContent = payload.payload_status || "unknown";
  const mode = byId("display-mode"); if (mode) mode.textContent = payload.display_mode === "redacted" ? "默认脱敏" : (payload.display_mode || "unknown");
}
function renderSafetyBadges(payload) { setSafeHtml("safety-badges", renderAssetBadges(payload.safety_badges || [])); }
function renderBlockedPayload(payload) {
  const banner = byId("blocked-banner"); if (!banner) return;
  if (payload.payload_status === "blocked") { banner.hidden = false; banner.textContent = "安全拦截：该 payload 已被阻断，页面不会显示任何真实值。"; }
  else { banner.hidden = true; banner.textContent = ""; }
}
const allowedObservationLabels = ["买入观察", "分批买入", "加仓观察", "减仓观察", "止盈观察", "止损观察", "清仓观察", "低吸区", "目标区", "风险位", "等待回调", "继续持有", "暂不操作", "个人观察", "风险提醒", "下一步关注"];
const forbiddenTradingExpressions = ["必须买入", "必须卖出", "立即满仓", "稳赚", "保证收益", "无风险", "自动下单", "系统替你操作", "系统建议你买入", "系统建议你卖出"];

function normalizeObservationLabel(label) {
  return String(label ?? "").trim();
}
function isAllowedObservationLabel(label) {
  return allowedObservationLabels.includes(normalizeObservationLabel(label));
}
function isForbiddenTradingExpression(text) {
  const value = String(text ?? "").replaceAll("不自动下单", "").replaceAll("不 自动下单", "");
  return forbiddenTradingExpressions.some((word) => value.includes(word));
}
function renderObservationCategoryBadge(category) {
  return `<span class="observation-badge category-badge">${escapeHtml(formatDisplayValue(category))}</span>`;
}
function renderObservationRiskBadge(riskLevel) {
  const risk = String(formatDisplayValue(riskLevel)).toLowerCase();
  const className = ["low", "medium", "high"].includes(risk) ? risk : "unknown";
  return `<span class="observation-badge risk-badge risk-${className}">${escapeHtml(formatDisplayValue(riskLevel))}</span>`;
}
function renderObservationStatusBadge(status) {
  return `<span class="observation-badge status-badge">${escapeHtml(formatDisplayValue(status))}</span>`;
}
function renderObservationPointCard(item = {}) {
  const label = normalizeObservationLabel(item.label) || "未提供";
  const safeLabel = isAllowedObservationLabel(label) ? label : "个人观察";
  const text = isForbiddenTradingExpression(item.text) ? "文案包含不允许表达，已隐藏。" : formatDisplayValue(item.text);
  const disclaimer = isForbiddenTradingExpression(item.disclaimer) ? "不构成强制交易指令。" : formatDisplayValue(item.disclaimer);
  return `<article class="observation-card">
    <header class="observation-card-header">
      <div><p class="observation-label-title">标签</p><h3>${escapeHtml(safeLabel)}</h3></div>
      <div class="observation-card-badges">${renderObservationCategoryBadge(item.category)}${renderObservationStatusBadge(item.status)}${renderObservationRiskBadge(item.risk_level)}</div>
    </header>
    <dl class="observation-meta">
      <dt>关联资产</dt><dd>${escapeHtml(formatDisplayValue(item.asset_name))}</dd>
      <dt>代码</dt><dd>${escapeHtml(formatDisplayValue(item.asset_code))}</dd>
      <dt>类型</dt><dd>${escapeHtml(formatDisplayValue(item.asset_type))}</dd>
      <dt>市场</dt><dd>${escapeHtml(formatDisplayValue(item.market))}</dd>
      <dt>观察点位</dt><dd>${renderRedactedValue(item.point_display)}</dd>
      <dt>当前状态</dt><dd>${renderObservationStatusBadge(item.status)}</dd>
      <dt>风险等级</dt><dd>${renderObservationRiskBadge(item.risk_level)}</dd>
      <dt>数据状态</dt><dd>${escapeHtml(formatDisplayValue(item.data_status || "demo-redacted"))}</dd>
      <dt>是否自动操作</dt><dd>否</dd>
    </dl>
    <p class="observation-text">${escapeHtml(text)}</p>
    <p class="observation-disclaimer">${escapeHtml(disclaimer)} 仅作为个人观察和记录，不自动下单，不构成强制交易指令。</p>
  </article>`;
}
function renderObservationPointCards(items = []) {
  if (!Array.isArray(items) || !items.length) return '<p class="empty-state">暂无个人观察点位。</p>';
  return items.map((item) => renderObservationPointCard(item)).join("");
}
function renderObservationEmptyState(section = {}) {
  if (section.enabled === false) return '<p class="empty-state">个人观察点位区域暂未启用。</p>';
  return '<p class="empty-state">暂无个人观察点位。</p>';
}
function renderObservationPoints(section = {}) {
  if (section.enabled === false) { setSafeHtml("observation-points-section", renderObservationEmptyState(section)); return; }
  const items = Array.isArray(section.items) ? section.items : [];
  const body = items.length ? renderObservationPointCards(items) : renderObservationEmptyState(section);
  setSafeHtml("observation-points-section", `<p class="section-note observation-page-note">仅作为个人观察和记录，不自动下单，不构成强制交易指令。</p>${body}`);
}
function renderWarnings(payload) {
  const warnings = payload.warnings || [];
  const items = warnings.length ? warnings : ["暂无额外风险提示"];
  setSafeHtml("warnings-section", items.map((text) => `<li>${escapeHtml(text)}</li>`).join(""));
}
function renderDisclaimer(payload) {
  const disclaimer = payload.disclaimer || "本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。";
  const node = byId("disclaimer-section"); if (node) node.textContent = disclaimer;
}
loadFinalPagePayload().then(renderFinalPagePayload);
