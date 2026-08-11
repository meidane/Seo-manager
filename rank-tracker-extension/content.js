// ============================================================
// Rank Tracker - Content Script
// اجرا فقط روی صفحات نتایج جستجوی گوگل (google.com/search)
// دامنه‌های هدف را از بک‌اند می‌گیرد (نه هاردکد)؛ جایگاه را روی خودِ نتیجه
// به‌صورتِ یک نشانِ سبزِ کوچک می‌نویسد — نه یک باکسِ ثابتِ گوشه‌ی صفحه.
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

function matchTrackedDomain(hostname, domains) {
  const h = (hostname || "").toLowerCase();
  return domains.find((d) => h === d.domain || h.endsWith("." + d.domain));
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
// نشانِ سبزِ جایگاه — کنارِ خودِ نتیجه، نه باکسِ ثابتِ گوشه‌ی صفحه
// ============================================================

function injectBadge(anchor, position) {
  const h3 = anchor.querySelector("h3");
  const host = h3 || anchor;
  if (host.querySelector(".rt-badge")) return; // از رندرِ دوباره (MutationObserver) جلوگیری کن
  const badge = document.createElement("span");
  badge.className = "rt-badge";
  badge.textContent = `جایگاه ${position}`;
  host.appendChild(badge);
}

// ============================================================
// اسکن صفحه + ارسال به بک‌اند
// ============================================================

let lastQuery = null;

async function processSearchPage() {
  const query = (getQueryParam("q") || "").trim();
  if (!query) return;
  // سرچ‌های site:/inurl:/... جستجوی واقعیِ کلمه‌ی کلیدی نیستند (تأییدِ ایندکس‌شدنِ
  // یک صفحه‌ی مشخص‌اند)؛ نباید به‌عنوانِ «کلمه‌ی کلیدی» ذخیره/ردیابی شوند.
  if (/^(site|inurl|intitle|intext|filetype|cache|related|link):/i.test(query)) return;

  const resp = await chrome.runtime.sendMessage({ type: "GET_TRACKED_DOMAINS" });
  if (!resp || !resp.ok) return; // تنظیم‌نشده یا خطای شبکه — بی‌سروصدا هیچ‌کاری نکن
  const domains = (resp.data && resp.data.domains) || [];
  if (!domains.length) return;

  const links = getOrganicResultLinks();
  const offset = getCurrentPageOffset();
  const newQuerySearch = query !== lastQuery;
  lastQuery = query;
  const seenThisPage = new Set();

  links.forEach((a, idx) => {
    const hostname = extractHostname(a.href);
    const matched = matchTrackedDomain(hostname, domains);
    if (!matched || seenThisPage.has(matched.domain)) return;
    seenThisPage.add(matched.domain);

    const position = offset + idx + 1;
    injectBadge(a, position);

    // فقط یک‌بار برای هر سرچِ جدید ارسال کن، نه با هر بار اجرای MutationObserver
    if (newQuerySearch || !a.dataset.rtReported) {
      a.dataset.rtReported = "1";
      chrome.runtime.sendMessage({
        type: "REPORT_RANK",
        // decodeURI نه decodeURIComponent: کاراکترهای رزرو‌شده‌ی URL (?،&،=،#) دست‌نخورده
        // می‌مانند، فقط حروفِ فارسیِ درصدرمزگذاری‌شده (٪D9%86...) خوانا می‌شوند.
        payload: { url: decodeURI(a.href), keyword: query, position },
      });
    }
  });
}

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
