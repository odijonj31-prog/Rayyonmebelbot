const tg = window.Telegram?.WebApp;

let CONFIG = { manager_username: "", has_ai: false };
let OPTIONS = { material: [], color: [], part: [] };
let BASE_RATE = 0;
let SELECTED_IDS = new Set();
let LAST_ESTIMATE = null; // { estimated_price, explanation }

function initTelegram() {
  if (!tg) return;
  tg.ready();
  tg.expand();
  try { tg.setHeaderColor("#0f0e0d"); } catch (e) {}
  try { tg.setBackgroundColor("#0f0e0d"); } catch (e) {}
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function fmtMoney(n) {
  if (n === null || n === undefined) return "—";
  return Math.round(n).toLocaleString("fr-FR").replace(/,/g, " ") + " so'm";
}

async function apiGet(path) {
  const res = await fetch(path);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  return res.json();
}

function withInitData(extra) {
  return { initData: tg?.initData || "", ...extra };
}

/* ============ VALIDATE + CONFIG ============ */

async function validateUser() {
  if (!tg || !tg.initData) return null;
  const data = await apiPost("/api/validate", withInitData({}));
  return data.ok ? data.user : null;
}

async function loadConfig() {
  const data = await apiGet("/api/config");
  if (data.ok) CONFIG = data;
}

/* ============ HOME ============ */

function setupManagerButton() {
  document.getElementById("manager-btn").addEventListener("click", () => {
    if (!CONFIG.manager_username) {
      tg?.showAlert?.("Menejer bilan bog'lanish hozircha sozlanmagan.");
      return;
    }
    tg?.openTelegramLink?.(`https://t.me/${CONFIG.manager_username}`);
  });
}

/* ============ KATALOG ============ */

async function loadPortfolio() {
  const grid = document.getElementById("portfolio-grid");
  const data = await apiGet("/api/portfolio");
  if (!data.ok || !data.items.length) return;

  grid.innerHTML = data.items.map(item => `
    <div class="portfolio-card">
      <img src="${item.photo_url}" alt="${escapeHtml(item.title)}" loading="lazy" />
      <div class="portfolio-card-info">
        <p class="portfolio-card-title">${escapeHtml(item.title)}</p>
        ${item.style_tags ? `<p class="portfolio-card-tags">${escapeHtml(item.style_tags)}</p>` : ""}
      </div>
    </div>
  `).join("");
}

/* ============ BUYURTMA (HISOBLAGICH) ============ */

const CATEGORY_LABELS = { material: "🧱 Xomashyo", color: "🎨 Rang", part: "🔧 Zapchast/aksessuar" };

async function loadOptions() {
  const data = await apiGet("/api/options");
  if (!data.ok) return;
  OPTIONS = data.options;
  BASE_RATE = data.base_price_per_sqm || 0;
  renderOptions();
}

function renderOptions() {
  const container = document.getElementById("options-container");
  let html = "";
  for (const cat of ["material", "color", "part"]) {
    const items = OPTIONS[cat] || [];
    if (!items.length) continue;
    html += `<div class="option-group">
      <div class="option-group-title">${CATEGORY_LABELS[cat]}</div>
      ${items.map(o => `
        <div class="option-chip" data-id="${o.id}">
          <div class="option-chip-left">
            <div class="option-checkbox">✓</div>
            <div class="option-name">${escapeHtml(o.name)}</div>
          </div>
          <div class="option-price">+${fmtMoney(o.extra_price)}</div>
        </div>
      `).join("")}
    </div>`;
  }
  container.innerHTML = html;

  container.querySelectorAll(".option-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const id = parseInt(chip.dataset.id);
      if (SELECTED_IDS.has(id)) SELECTED_IDS.delete(id); else SELECTED_IDS.add(id);
      chip.classList.toggle("selected");
      updateLivePrice();
      if (tg?.HapticFeedback) { try { tg.HapticFeedback.selectionChanged(); } catch (e) {} }
    });
  });
}

function getAllOptionsFlat() {
  return [...OPTIONS.material, ...OPTIONS.color, ...OPTIONS.part];
}

function computeLiveTotal() {
  const width = parseInt(document.getElementById("width-input").value) || 0;
  const height = parseInt(document.getElementById("height-input").value) || 0;
  const sqm = (width / 1000) * (height / 1000);
  const base = Math.round(sqm * BASE_RATE);
  const flat = getAllOptionsFlat();
  let optionsTotal = 0;
  flat.forEach(o => { if (SELECTED_IDS.has(o.id)) optionsTotal += o.extra_price; });
  return base + optionsTotal;
}

function updateLivePrice() {
  const total = computeLiveTotal();
  document.getElementById("price-bar-value").textContent = fmtMoney(total);
  document.getElementById("price-bar").classList.remove("hidden");
  // O'lcham yoki tanlov o'zgarsa, eski AI tushuntirishi va formani yashiramiz — qayta hisoblash kerak
  document.getElementById("ai-explain-card").classList.add("hidden");
  document.getElementById("order-form").classList.add("hidden");
  LAST_ESTIMATE = null;
}

function syncSliderAndInput(sliderId, inputId) {
  const slider = document.getElementById(sliderId);
  const input = document.getElementById(inputId);
  slider.addEventListener("input", () => { input.value = slider.value; updateLivePrice(); });
  input.addEventListener("input", () => { slider.value = input.value; updateLivePrice(); });
}

async function handleCalculate() {
  const width = parseInt(document.getElementById("width-input").value) || 0;
  const height = parseInt(document.getElementById("height-input").value) || 0;
  if (width <= 0 || height <= 0) {
    tg?.showAlert?.("Iltimos, o'lchamni to'g'ri kiriting.");
    return;
  }

  const btn = document.getElementById("calc-btn");
  btn.textContent = "⏳...";
  btn.disabled = true;

  const data = await apiPost("/api/estimate", {
    width_mm: width,
    height_mm: height,
    option_ids: [...SELECTED_IDS],
  });

  btn.textContent = "🧮 Hisoblash";
  btn.disabled = false;

  if (!data.ok) {
    tg?.showAlert?.("Xatolik yuz berdi, qayta urinib ko'ring.");
    return;
  }

  LAST_ESTIMATE = data;
  document.getElementById("price-bar-value").textContent = fmtMoney(data.estimated_price);
  document.getElementById("ai-explain-text").textContent = data.explanation;
  document.getElementById("ai-explain-card").classList.remove("hidden");
  document.getElementById("order-form").classList.remove("hidden");

  document.getElementById("order-form").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function handleSubmitOrder() {
  if (!LAST_ESTIMATE) return;
  const name = document.getElementById("contact-name").value.trim();
  const phone = document.getElementById("contact-phone").value.trim();
  const comment = document.getElementById("contact-comment").value.trim();

  if (!name || !phone) {
    tg?.showAlert?.("Iltimos, ism va telefon raqamingizni kiriting.");
    return;
  }

  const width = parseInt(document.getElementById("width-input").value) || 0;
  const height = parseInt(document.getElementById("height-input").value) || 0;

  const btn = document.getElementById("submit-order-btn");
  btn.textContent = "⏳ Yuborilmoqda...";
  btn.disabled = true;

  const data = await apiPost("/api/orders", withInitData({
    width_mm: width,
    height_mm: height,
    option_ids: [...SELECTED_IDS],
    estimated_price: LAST_ESTIMATE.estimated_price,
    description: comment || null,
    contact_name: name,
    contact_phone: phone,
  }));

  btn.textContent = "✅ Buyurtma qoldirish";
  btn.disabled = false;

  if (!data.ok) {
    tg?.showAlert?.("Xatolik yuz berdi, qayta urinib ko'ring.");
    return;
  }

  tg?.showPopup?.({
    title: "✅ Qabul qilindi!",
    message: `Buyurtmangiz #${data.order_id} raqami bilan qabul qilindi. Menejerimiz tez orada bog'lanadi!`,
    buttons: [{ type: "ok" }],
  });

  // Formani tozalab, Buyurtmalarim'ga o'tamiz
  document.getElementById("contact-name").value = "";
  document.getElementById("contact-phone").value = "";
  document.getElementById("contact-comment").value = "";
  document.getElementById("order-form").classList.add("hidden");
  document.getElementById("ai-explain-card").classList.add("hidden");
  SELECTED_IDS.clear();
  renderOptions();

  switchTab("tab-orders");
  loadMyOrders();
}

/* ============ BUYURTMALARIM ============ */

const STATUS_STEPS = [
  { key: "new", title: "Buyurtma qabul qilindi" },
  { key: "confirmed", title: "Kelishuv va to'lov" },
  { key: "in_production", title: "Ishlab chiqarilmoqda" },
  { key: "delivered", title: "Yetkazish va o'rnatish" },
];

function renderTimeline(status) {
  if (status === "cancelled") {
    return `<div class="timeline"><div class="timeline-step done">
      <div class="timeline-dot">✕</div>
      <div><div class="timeline-text-title">Bekor qilingan</div></div>
    </div></div>`;
  }
  const currentIndex = STATUS_STEPS.findIndex(s => s.key === status);
  return `<div class="timeline">${STATUS_STEPS.map((s, i) => {
    const cls = i < currentIndex ? "done" : i === currentIndex ? "current" : "";
    const icon = i < currentIndex ? "✓" : i === currentIndex ? "●" : "";
    const sub = i < currentIndex ? "Bajarildi" : i === currentIndex ? "Hozirgi jarayon" : "Kutilmoqda";
    return `<div class="timeline-step ${cls}">
      <div class="timeline-dot">${icon}</div>
      <div>
        <div class="timeline-text-title">${s.title}</div>
        <div class="timeline-text-sub">${sub}</div>
      </div>
    </div>`;
  }).join("")}</div>`;
}

function renderPaymentBox(order) {
  if (!order.agreed_price) {
    return `<div class="payment-box"><div class="payment-row"><span>Holat</span><span>Narx hali kelishilmagan</span></div></div>`;
  }
  return `<div class="payment-box">
    <div class="payment-row"><span>Kelishilgan summa</span><span>${fmtMoney(order.agreed_price)}</span></div>
    <div class="payment-row"><span>To'langan</span><span>${fmtMoney(order.paid)}</span></div>
    <div class="payment-row"><span>Qarzdorlik</span><span>${fmtMoney(order.debt)}</span></div>
  </div>`;
}

async function loadMyOrders() {
  const list = document.getElementById("orders-list");
  const data = await apiPost("/api/orders/mine", withInitData({}));
  if (!data.ok || !data.orders.length) return;

  list.innerHTML = data.orders.map(o => `
    <div class="order-card ${o.status === 'cancelled' ? 'order-status-cancelled' : ''}">
      <div class="order-card-header">
        <div class="order-card-id">Buyurtma #${o.id}</div>
        <div class="order-card-dim">${o.width_mm}×${o.height_mm} mm</div>
      </div>
      ${renderTimeline(o.status)}
      ${renderPaymentBox(o)}
    </div>
  `).join("");
}

/* ============ TABS ============ */

function switchTab(tabId) {
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === tabId));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.toggle("active", p.id === tabId));
  document.getElementById("price-bar").classList.toggle("hidden", tabId !== "tab-order" || SELECTED_IDS.size === 0 && computeLiveTotal() === 0);
  if (tabId === "tab-order") updateLivePrice();
  if (tabId === "tab-orders") loadMyOrders();
}

function setupTabs() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      switchTab(btn.dataset.tab);
      if (tg?.HapticFeedback) { try { tg.HapticFeedback.impactOccurred("light"); } catch (e) {} }
    });
  });
}

/* ============ MAIN ============ */

async function main() {
  initTelegram();
  setupTabs();
  setupManagerButton();

  syncSliderAndInput("width-slider", "width-input");
  syncSliderAndInput("height-slider", "height-input");
  document.getElementById("calc-btn").addEventListener("click", handleCalculate);
  document.getElementById("submit-order-btn").addEventListener("click", handleSubmitOrder);

  await Promise.all([loadConfig(), validateUser(), loadPortfolio(), loadOptions()]);

  document.getElementById("splash").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
}

main();
    
