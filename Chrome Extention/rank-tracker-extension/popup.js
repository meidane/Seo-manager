const STORAGE_KEY = "rankTrackerData";
const SETTINGS_KEY = "rankTrackerSettings";

async function loadData() {
  const data = await chrome.storage.local.get(STORAGE_KEY);
  return data[STORAGE_KEY] || {};
}

function render(data) {
  const listEl = document.getElementById("list");
  const queries = Object.keys(data).sort(
    (a, b) => (data[b].lastUpdated || 0) - (data[a].lastUpdated || 0)
  );

  if (queries.length === 0) {
    listEl.innerHTML = `<div class="empty">هنوز هیچ سرچی ثبت نشده است.</div>`;
    return;
  }

  listEl.innerHTML = queries.map(q => {
    const entry = data[q];
    const rows = Object.keys(entry.results).map(domain => {
      const r = entry.results[domain];
      const cls = r.position === -1 ? "not-found" : "found";
      const text = r.position === -1 ? "یافت نشد" : `جایگاه ${r.position}`;
      return `<div class="row"><span class="domain">${domain}</span><span class="${cls}">${text}</span></div>`;
    }).join("");

    return `<div class="entry"><div class="query">${q}</div>${rows}</div>`;
  }).join("");
}

async function init() {
  const data = await loadData();
  render(data);

  const settings = await chrome.storage.local.get(SETTINGS_KEY);
  const apiUrlInput = document.getElementById("apiUrl");
  if (settings[SETTINGS_KEY] && settings[SETTINGS_KEY].apiUrl) {
    apiUrlInput.value = settings[SETTINGS_KEY].apiUrl;
  }

  document.getElementById("clearBtn").addEventListener("click", async () => {
    await chrome.storage.local.remove(STORAGE_KEY);
    render({});
  });

  document.getElementById("saveApiBtn").addEventListener("click", async () => {
    const value = apiUrlInput.value.trim();
    await chrome.storage.local.set({ [SETTINGS_KEY]: { apiUrl: value } });
    alert("ذخیره شد.");
  });
}

init();
