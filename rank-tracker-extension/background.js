// ============================================================
// Rank Tracker — Background Service Worker
// تنها جایی که با بک‌اندِ پلتفرم صحبت می‌کند (توکنِ API را اینجا نگه می‌داریم،
// نه در content.js که در صفحه‌ی گوگل اجرا می‌شود).
// ============================================================

const SETTINGS_KEY = "rankTrackerSettings"; // { apiBaseUrl, apiToken }
const CACHE_TTL_MS = 10 * 60 * 1000; // ۱۰ دقیقه — تا هر سرچ یک درخواستِ جدا نزند

let domainsCache = null;
let domainsCacheAt = 0;

async function getSettings() {
  const s = await chrome.storage.local.get(SETTINGS_KEY);
  const cfg = s[SETTINGS_KEY] || {};
  return {
    apiBaseUrl: (cfg.apiBaseUrl || "").trim().replace(/\/+$/, ""),
    apiToken: (cfg.apiToken || "").trim(),
  };
}

async function apiFetch(path, options) {
  const { apiBaseUrl, apiToken } = await getSettings();
  if (!apiBaseUrl || !apiToken) return { ok: false, error: "not_configured" };
  try {
    const res = await fetch(apiBaseUrl + path, {
      ...options,
      headers: {
        Authorization: `Token ${apiToken}`,
        ...(options && options.headers),
      },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return { ok: false, error: `http_${res.status}`, detail: data.detail };
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: "network" };
  }
}

async function getTrackedDomains(force) {
  const now = Date.now();
  if (!force && domainsCache && now - domainsCacheAt < CACHE_TTL_MS) {
    return { ok: true, data: domainsCache };
  }
  const r = await apiFetch("/seo/api/tracked-domains/", { method: "GET" });
  if (r.ok) {
    domainsCache = r.data;
    domainsCacheAt = now;
  }
  return r;
}

async function reportRank(payload) {
  return apiFetch("/seo/api/rank-ingest/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function pushRecent(entry) {
  const { recent = [] } = await chrome.storage.local.get("recent");
  recent.unshift({ ...entry, at: Date.now() });
  await chrome.storage.local.set({ recent: recent.slice(0, 30) });
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "GET_TRACKED_DOMAINS") {
    getTrackedDomains(false).then(sendResponse);
    return true;
  }
  if (msg.type === "TEST_CONNECTION") {
    getTrackedDomains(true).then(sendResponse);
    return true;
  }
  if (msg.type === "REPORT_RANK") {
    reportRank(msg.payload).then((r) => {
      pushRecent({ ...msg.payload, ok: r.ok, matched: r.data && r.data.matched });
      sendResponse(r);
    });
    return true;
  }
  return false;
});
