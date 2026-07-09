const fallbackPayload = {
  account_id: "demo_account",
  account_name: "示例账户",
  payload_status: "safe_for_account_page",
  display_mode: "redacted",
  data_mode: "dry_run",
  can_write_to_public_repo: false,
  sections: {
    stock_etf: { enabled: false, title: "股票 / ETF 行情", display_models: [] },
    fund_nav: { enabled: false, title: "场外基金净值", display_models: [] },
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
    "场外基金盘中估算仅供观察，最终以基金公司公布净值为准。"
  ],
  disclaimer: "本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。"
};

function getFallbackPayload() {
  return fallbackPayload;
}

function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;"
  }[char]));
}

function setSafeHtml(id, html) {
  const node = byId(id);
  if (node) node.innerHTML = html;
}

async function loadFinalPagePayload() {
  try {
    const response = await fetch("demo_final_page_payload.json");
    if (!response.ok) throw new Error("Cannot load local demo payload");
    return await response.json();
  } catch (error) {
    return fallbackPayload;
  }
}

function renderFinalPagePayload(payload) {
  const safePayload = payload || getFallbackPayload();
  renderAccountHeader(safePayload);
  renderSafetyBadges(safePayload);
  renderBlockedPayload(safePayload);
  if (safePayload.payload_status === "blocked") {
    setSafeHtml("stock-etf-section", '<p class="empty-state">安全拦截状态下不显示股票 / ETF 真实值</p>');
    setSafeHtml("fund-nav-section", '<p class="empty-state">安全拦截状态下不显示场外基金净值真实值</p><p class="section-note">盘中估算仅供观察，最终以基金公司公布净值为准。</p>');
    setSafeHtml("observation-points-section", '<p class="empty-state">安全拦截状态下不显示上游原始内容</p>');
    renderWarnings(safePayload);
    renderDisclaimer(safePayload);
    return;
  }
  renderStockEtfSection(safePayload.sections?.stock_etf);
  renderFundNavSection(safePayload.sections?.fund_nav);
  renderObservationPoints(safePayload.sections?.observation_points);
  renderWarnings(safePayload);
  renderDisclaimer(safePayload);
}

function renderAccountHeader(payload) {
  const name = byId("account-name");
  if (name) name.textContent = payload.account_name || "示例账户";
  const status = byId("payload-status");
  if (status) status.textContent = payload.payload_status || "unknown";
  const mode = byId("display-mode");
  if (mode) mode.textContent = payload.display_mode === "redacted" ? "默认脱敏" : (payload.display_mode || "unknown");
}

function renderSafetyBadges(payload) {
  const badges = payload.safety_badges || [];
  setSafeHtml("safety-badges", badges.map((text) => `<span class="badge">${escapeHtml(text)}</span>`).join(""));
}

function renderBlockedPayload(payload) {
  const banner = byId("blocked-banner");
  if (!banner) return;
  if (payload.payload_status === "blocked") {
    banner.hidden = false;
    banner.textContent = "安全拦截：该 payload 已被阻断，页面不会显示任何真实值。";
  } else {
    banner.hidden = true;
    banner.textContent = "";
  }
}

function renderStockEtfSection(section = {}) {
  if (section.enabled === false) {
    setSafeHtml("stock-etf-section", '<p class="empty-state">股票 / ETF 区域暂未启用</p>');
    return;
  }
  const models = section.display_models || [];
  const cards = models.map((model) => {
    const quote = model.quote_display || {};
    return `<article class="asset-card">
      <div><strong>${escapeHtml(model.name)}</strong><span>${escapeHtml(model.code)} · ${escapeHtml(model.market)} · ${escapeHtml(model.type)}</span></div>
      <dl><dt>最新价</dt><dd>${escapeHtml(quote.last_price || "<redacted>")}</dd><dt>涨跌幅</dt><dd>${escapeHtml(quote.change_pct || "<redacted>")}</dd><dt>成交额</dt><dd>${escapeHtml(quote.turnover || "<redacted>")}</dd></dl>
      <div class="badge-row compact">${(model.badges || []).map((text) => `<span class="badge">${escapeHtml(text)}</span>`).join("")}</div>
    </article>`;
  }).join("");
  setSafeHtml("stock-etf-section", cards || '<p class="empty-state">股票 / ETF 区域暂无可展示项目</p>');
}

function renderFundNavSection(section = {}) {
  if (section.enabled === false) {
    setSafeHtml("fund-nav-section", '<p class="empty-state">场外基金净值区域暂未启用</p>');
    return;
  }
  const models = section.display_models || [];
  const cards = models.map((model) => {
    const nav = model.nav_display || {};
    const estimate = model.estimate_display || {};
    return `<article class="asset-card">
      <div><strong>${escapeHtml(model.name)}</strong><span>${escapeHtml(model.code)} · ${escapeHtml(model.market)} · ${escapeHtml(model.type)}</span></div>
      <dl><dt>单位净值</dt><dd>${escapeHtml(nav.unit_nav || "<redacted>")}</dd><dt>累计净值</dt><dd>${escapeHtml(nav.accumulated_nav || "<redacted>")}</dd><dt>净值日期</dt><dd>${escapeHtml(nav.nav_date || "demo-date")}</dd><dt>估算净值</dt><dd>${escapeHtml(estimate.estimated_nav || "<redacted>")}</dd><dt>估算时间</dt><dd>${escapeHtml(estimate.estimate_time || "demo-time")}</dd></dl>
      <p class="section-note">盘中估算仅供观察，最终以基金公司公布净值为准。</p>
      <div class="badge-row compact">${(model.badges || []).map((text) => `<span class="badge">${escapeHtml(text)}</span>`).join("")}</div>
    </article>`;
  }).join("");
  setSafeHtml("fund-nav-section", cards || '<p class="empty-state">场外基金净值区域暂无可展示项目</p><p class="section-note">盘中估算仅供观察，最终以基金公司公布净值为准。</p>');
}

function renderObservationPoints(section = {}) {
  const items = section.items || [];
  if (!items.length) {
    setSafeHtml("observation-points-section", '<p class="empty-state">暂无个人观察点位</p>');
    return;
  }
  const html = items.map((item) => `<div class="observation-item"><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.text)}</span></div>`).join("");
  setSafeHtml("observation-points-section", html);
}

function renderWarnings(payload) {
  const warnings = payload.warnings || [];
  const items = warnings.length ? warnings : ["暂无额外风险提示"];
  setSafeHtml("warnings-section", items.map((text) => `<li>${escapeHtml(text)}</li>`).join(""));
}

function renderDisclaimer(payload) {
  const disclaimer = payload.disclaimer || "本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。";
  const node = byId("disclaimer-section");
  if (node) node.textContent = disclaimer;
}

loadFinalPagePayload().then(renderFinalPagePayload);
