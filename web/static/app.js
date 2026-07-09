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
        { label: "买入观察", text: "仅作为个人观察记录，不自动下单。" },
        { label: "加仓观察", text: "等待回调确认后再记录。" },
        { label: "止盈观察", text: "接近目标区时重点观察。" },
        { label: "风险位", text: "跌破关键位置时提高风险等级。" }
      ]
    }
  },
  safety_badges: ["已审计", "默认脱敏", "禁止写入真实数据"],
  warnings: [
    "本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。",
    "盘中估算仅供观察，最终以基金公司公布净值为准。"
  ],
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
  return `<article class="asset-card blocked-card">${renderAssetHeader(model)}<p class="blocked-message">数据已被安全闸门拦截，不显示真实行情。</p><dl>${renderMetaRows(model)}</dl><div class="badge-row compact">${renderAssetBadges(model.badges)}</div></article>`;
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
function renderMarketDashboard(payload) {
  const sections = payload?.sections || {};
  setSafeHtml("stock-etf-section", renderStockEtfCards(sections.stock_etf || {}));
  setSafeHtml("fund-nav-section", renderFundNavCards(sections.fund_nav || {}));
}

function renderFinalPagePayload(payload) {
  const safePayload = payload || getFallbackPayload();
  renderAccountHeader(safePayload); renderSafetyBadges(safePayload); renderBlockedPayload(safePayload);
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
function renderObservationPoints(section = {}) {
  const items = section.items || [];
  if (!items.length) { setSafeHtml("observation-points-section", '<p class="empty-state">暂无个人观察点位</p>'); return; }
  setSafeHtml("observation-points-section", items.map((item) => `<div class="observation-item"><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.text)}</span></div>`).join(""));
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
