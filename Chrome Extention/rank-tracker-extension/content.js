// ============================================================
// Rank Tracker - Content Script
// اجرا فقط روی صفحات نتایج جستجوی گوگل (google.com/search)
// ============================================================

// --- ۱) لیست سایت‌های هدف (فعلا هاردکد، بعدا میشه از storage خواند) ---
const TARGET_DOMAINS = [
  "iransunlight.com",
  "arshianclinic.com",
  "meidane.com"
];

// نتایج معمولی گوگل در هر صفحه چند تا هستند (برای محاسبه‌ی جایگاه واقعی)
const RESULTS_PER_PAGE = 10;

// ============================================================
// توابع کمکی
// ============================================================

function getQueryParam(name) {
  const url = new URL(window.location.href);
  return url.searchParams.get(name);
}

// شماره صفحه فعلی (۰-بیس => start=0 صفحه ۱, start=10 صفحه ۲, ...)
function getCurrentPageOffset() {
  const start = parseInt(getQueryParam("start") || "0", 10);
  return isNaN(start) ? 0 : start;
}

function extractHostname(href) {
  try {
    return new URL(href).hostname.replace(/^www\./, "");
  } catch (e) {
    return "";
  }
}

function matchTargetDomain(hostname) {
  return TARGET_DOMAINS.find(d => hostname === d || hostname.endsWith("." + d));
}

// لیست "کارت‌های نتیجه" واقعی صفحه (چیزی که کاربر با چشم می‌شمارد: ۱، ۲، ۳...)
//
// چرا از h3 به‌تنهایی استفاده نمی‌کنیم؟
// چون "People also ask" و بعضی بلوک‌های دیگر هم h3 دارند و باعث شمارش اشتباه می‌شوند
// (مثلا جایگاه ۱۱ به‌جای ۷ در تست واقعی).
//
// راه‌حل مطمئن‌تر: گوگل برای هر نتیجه‌ی واقعی (از جمله Featured Snippet) یک تگ
// <cite> برای نمایش آدرس سایت رندر می‌کند. ما از روی <cite>ها بالا می‌رویم تا
// نزدیک‌ترین لینک نتیجه (a > h3) را پیدا کنیم؛ این یعنی فقط "کارت‌های نتیجه‌ی واقعی"
// شمارش می‌شوند، نه هر h3 پراکنده‌ای در صفحه (مثل People also ask).
function getOrganicResultLinks() {
  const container = document.getElementById("search") || document.body;
  const cites = Array.from(container.querySelectorAll("cite"));

  const seen = new Set();
  const links = [];

  for (const cite of cites) {
    let block = cite;
    let a = null;

    // چند سطح بالا می‌رویم تا بلوکی پیدا شود که هم cite هم h3+لینک دارد
    for (let i = 0; i < 8 && block; i++, block = block.parentElement) {
      const candidate = block.querySelector("a h3");
      if (candidate) {
        a = candidate.closest("a");
        break;
      }
    }

    if (!a || !a.href) continue;

    // حذف تبلیغات
    if (a.closest("#tads") || a.closest("#tadsb") || a.closest("#bottomads")) continue;

    // حذف موارد تکراری (sitelinks چندتایی زیر یک نتیجه، یا چند cite برای یک نتیجه)
    const key = a.href.split("#")[0];
    if (seen.has(key)) continue;
    seen.add(key);

    links.push(a);
  }
  return links;
}

// ============================================================
// اسکن صفحه فعلی و پیدا کردن جایگاه سایت‌های هدف
// ============================================================

function scanCurrentPage() {
  const offset = getCurrentPageOffset();
  const links = getOrganicResultLinks();

  const found = {}; // { domain: { position, url } }

  links.forEach((a, idx) => {
    const hostname = extractHostname(a.href);
    const matched = matchTargetDomain(hostname);
    if (matched && !found[matched]) {
      found[matched] = {
        position: offset + idx + 1, // جایگاه واقعی با احتساب صفحه
        url: a.href
      };
    }
  });

  return found;
}

// ============================================================
// ذخیره‌سازی نتایج (فعلا در chrome.storage.local، بعدا API خارجی)
// ============================================================

const STORAGE_KEY = "rankTrackerData";

async function loadStoredData() {
  const data = await chrome.storage.local.get(STORAGE_KEY);
  return data[STORAGE_KEY] || {};
}

async function saveStoredData(data) {
  await chrome.storage.local.set({ [STORAGE_KEY]: data });
}

// این تابع فعلا فقط داخل storage محلی ذخیره می‌کند.
// بعدا اینجا یک fetch/POST به بک‌اند دیتابیس اضافه می‌شود.
async function sendToRemoteDatabase(keyword, resultsForKeyword) {
  // TODO: وقتی بک‌اند و آدرس API آماده شد، اینجا پیاده‌سازی شود:
  //
  // await fetch("https://YOUR-BACKEND-DOMAIN/api/rank", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({ keyword, results: resultsForKeyword, timestamp: Date.now() })
  // });
  //
  // فعلا فقط لاگ می‌گیریم:
  console.log("[RankTracker] (stub) sendToRemoteDatabase:", keyword, resultsForKeyword);
}

// ============================================================
// منطق اصلی: هر سرچ جدید = ریست به -۱، هر بار که پیدا شد آپدیت می‌شود
// ============================================================

async function processSearchPage() {
  const query = (getQueryParam("q") || "").trim();
  if (!query) return;

  const allData = await loadStoredData();

  // اگر این کوئری برای اولین‌بار است، مقدار همه‌ی دامنه‌ها را -۱ بگذار
  if (!allData[query]) {
    allData[query] = {
      firstSeen: Date.now(),
      lastUpdated: Date.now(),
      results: {}
    };
    TARGET_DOMAINS.forEach(d => {
      allData[query].results[d] = { position: -1, url: null };
    });
  }

  const foundOnThisPage = scanCurrentPage();

  // فقط دامنه‌هایی که در این صفحه واقعا دیده شدند آپدیت می‌شوند
  Object.keys(foundOnThisPage).forEach(domain => {
    allData[query].results[domain] = foundOnThisPage[domain];
  });

  allData[query].lastUpdated = Date.now();

  await saveStoredData(allData);
  await sendToRemoteDatabase(query, allData[query].results);

  renderOverlay(query, allData[query].results);
}

// ============================================================
// نمایش یک باکس کوچک روی صفحه گوگل با وضعیت فعلی
// ============================================================

function renderOverlay(query, results) {
  let box = document.getElementById("rank-tracker-overlay");
  if (!box) {
    box = document.createElement("div");
    box.id = "rank-tracker-overlay";
    document.body.appendChild(box);
  }

  // فقط دامنه‌هایی که پیدا شده‌اند نمایش داده می‌شوند؛ "یافت نشد" اصلا رندر نمی‌شود
  const foundDomains = TARGET_DOMAINS.filter(
    domain => results[domain] && results[domain].position !== -1
  );

  const rows = foundDomains
    .map(domain => {
      const r = results[domain];
      return `<div class="rt-row"><span class="rt-domain">${domain}</span><span class="rt-found">جایگاه ${r.position}</span></div>`;
    })
    .join("");

  const body =
    rows || `<div class="rt-empty">هنوز در این صفحه چیزی پیدا نشده</div>`;

  box.innerHTML = `
    <div class="rt-header">
      Rank Tracker
      <span class="rt-close" id="rt-close-btn">&times;</span>
    </div>
    <div class="rt-query">کوئری: ${query}</div>
    ${body}
    <div class="rt-hint">برای بررسی صفحه‌های بعدی، خودتان به صفحه ۲/۳/... بروید.</div>
  `;

  const closeBtn = document.getElementById("rt-close-btn");
  if (closeBtn) closeBtn.addEventListener("click", () => box.remove());
}

// ============================================================
// اجرا
// ============================================================

// کمی تاخیر تا مطمئن شویم نتایج گوگل کامل رندر شده‌اند
setTimeout(processSearchPage, 600);

// در صورتی که گوگل نتایج را با تاخیر/AJAX (اسکرول بی‌نهایت) اضافه کند
const observer = new MutationObserver(() => {
  clearTimeout(window.__rtDebounce);
  window.__rtDebounce = setTimeout(processSearchPage, 800);
});
const searchRoot = document.getElementById("search");
if (searchRoot) {
  observer.observe(searchRoot, { childList: true, subtree: true });
}
