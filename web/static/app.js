const fallbackPayload = {
  account_name: "示例账户",
  safety_badges: ["已审计", "默认脱敏", "禁止写入真实数据"],
  sections: {
    observation_points: {
      items: [
        { label: "买入观察", text: "仅作为个人观察记录，不自动下单。" },
        { label: "加仓观察", text: "等待回调确认后再记录。" },
        { label: "止盈观察", text: "接近目标区时重点观察。" },
        { label: "风险位", text: "跌破关键位置时提高风险等级。" }
      ]
    }
  },
  warnings: ["本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。"],
  disclaimer: "本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。"
};

function renderPayload(payload) {
  document.getElementById("account-name").textContent = payload.account_name || "示例账户";

  const badges = document.getElementById("safety-badges");
  badges.innerHTML = "";
  (payload.safety_badges || []).forEach((text) => {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = text;
    badges.appendChild(badge);
  });

  const points = document.getElementById("observation-points");
  points.innerHTML = "";
  const items = payload.sections?.observation_points?.items || [];
  items.forEach((item) => {
    const node = document.createElement("div");
    node.className = "observation-item";
    const label = document.createElement("strong");
    label.textContent = item.label;
    const text = document.createElement("span");
    text.textContent = item.text;
    node.append(label, text);
    points.appendChild(node);
  });

  const warnings = document.getElementById("warnings");
  warnings.innerHTML = "";
  (payload.warnings || fallbackPayload.warnings).forEach((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    warnings.appendChild(item);
  });

  document.getElementById("disclaimer").textContent = payload.disclaimer || fallbackPayload.disclaimer;
}

fetch("demo_final_page_payload.json")
  .then((response) => {
    if (!response.ok) {
      throw new Error("Cannot load local demo payload");
    }
    return response.json();
  })
  .then(renderPayload)
  .catch(() => renderPayload(fallbackPayload));
