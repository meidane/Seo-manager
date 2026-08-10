const SETTINGS_KEY = "rankTrackerSettings";

function fmtAgo(ts) {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return "همین حالا";
  if (s < 3600) return `${Math.floor(s / 60)} دقیقه پیش`;
  if (s < 86400) return `${Math.floor(s / 3600)} ساعت پیش`;
  return `${Math.floor(s / 86400)} روز پیش`;
}

function renderRecent(recent) {
  const listEl = document.getElementById("list");
  if (!recent || !recent.length) {
    listEl.innerHTML = `<div class="empty">هنوز هیچ موردی ثبت نشده است.</div>`;
    return;
  }
  listEl.innerHTML = recent
    .map((r) => {
      const cls = r.matched ? "found" : "not-found";
      const text = r.matched ? `جایگاه ${r.position}` : "بی‌ربط به پروژه‌ها";
      return `<div class="entry">
        <div class="query">${r.keyword}</div>
        <div class="row"><span class="domain">${new URL(r.url).hostname}</span><span class="${cls}">${text}</span></div>
        <div class="row"><span class="domain">${fmtAgo(r.at)}</span></div>
      </div>`;
    })
    .join("");
}

function setStatus(msg, ok) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = "status " + (ok === true ? "ok" : ok === false ? "err" : "");
}

async function init() {
  const { recent = [] } = await chrome.storage.local.get("recent");
  renderRecent(recent);

  const stored = await chrome.storage.local.get(SETTINGS_KEY);
  const cfg = stored[SETTINGS_KEY] || {};
  document.getElementById("apiUrl").value = cfg.apiBaseUrl || "";
  document.getElementById("apiToken").value = cfg.apiToken || "";
  if (cfg.apiBaseUrl && cfg.apiToken) setStatus("تنظیم شده — روی «تست اتصال» بزن", null);

  document.getElementById("saveBtn").addEventListener("click", async () => {
    const apiBaseUrl = document.getElementById("apiUrl").value.trim();
    const apiToken = document.getElementById("apiToken").value.trim();
    await chrome.storage.local.set({ [SETTINGS_KEY]: { apiBaseUrl, apiToken } });
    setStatus("ذخیره شد", true);
  });

  document.getElementById("testBtn").addEventListener("click", async () => {
    setStatus("در حال بررسی…", null);
    const resp = await chrome.runtime.sendMessage({ type: "TEST_CONNECTION" });
    if (resp && resp.ok) {
      const n = (resp.data && resp.data.domains && resp.data.domains.length) || 0;
      setStatus(`متصل — ${n} دامنه در حال ردیابی`, true);
    } else {
      const reason = (resp && resp.error) || "نامشخص";
      setStatus(`اتصال ناموفق (${reason})`, false);
    }
  });

  document.getElementById("clearBtn").addEventListener("click", async () => {
    await chrome.storage.local.remove("recent");
    renderRecent([]);
  });
}

init();
