// پرامپت‌ها/رقبای نمونه‌ای که موقعِ ساختِ سایتِ جدید کپی می‌شوند (بعدش برای هر سایت جدا و قابلِ ویرایش‌اند).

export const STEP_KEYS = ['competitors', 'serp', 'suggest', 'internal_links', 'images'];
export const STEP_LABELS = { competitors: 'بررسی رقبا', serp: 'نتایج گوگل و سؤالات مرتبط', suggest: 'گوگل ساجست', internal_links: 'لینک داخلی', images: 'عکس' };

const steps = (on, n) => ({ competitors: on.includes('competitors'), competitors_n: n || 5, serp: on.includes('serp'),
  suggest: on.includes('suggest'), internal_links: on.includes('internal_links'), images: on.includes('images') });

export const DEFAULT_PROMPTS = [
  { kind: 'general', title: 'قواعد نگارش', use: '', body:
`فارسیِ روان و طبیعی بنویس؛ جمله‌های کوتاه، بدونِ تکرارِ مکانیکیِ کلمهٔ کلیدی و بدونِ اغراق. متنِ رقبا فقط برای ایده است؛ هرگز کپی نکن.
همه‌چیز پیش‌نویس (draft) ذخیره شود؛ انتشار فقط با تأییدِ من.` },
  { kind: 'general', title: 'برند و لحن', use: '', body: 'نامِ برند، مخاطب و لحنِ این سایت را اینجا بنویس (مثلاً: برند استیل تک، مخاطب خریدارانِ صنعتی، لحنِ تخصصی ولی ساده).' },
  { kind: 'specific', title: 'مقاله جدید', use: 'مقاله', steps: steps(['competitors', 'serp', 'suggest', 'internal_links', 'images'], 5), body:
`یک مقالهٔ کامل و طبیعی بنویس.
۱) ساختار: H1 شامل کلمهٔ کلیدی؛ H2/H3هایی که سرفصل‌های مشترکِ رقبا را پوشش دهد + حداقل ۲ بخش که رقبا ندارند.
۲) طول: حدودِ میانهٔ رقبا تا ۲۰٪ بیشتر، بدونِ پرگویی. ۳) مقدمهٔ کوتاه که مستقیم به جوابِ کاربر برسد.
۴) جدول یا فهرست هرجا مقایسه/مراحل هست. ۵) «سؤالات متداول» از سؤالاتِ مرتبط و ساجست.
۶) ۳ تا ۸ لینکِ داخلی با انکرِ طبیعی. ۷) یک تصویرِ شاخص + ۱ تا ۳ عکسِ داخلِ متن با alt توصیفی.
۸) عنوانِ سئو ≤ ۶۰ نویسه و توضیحِ متا ≤ ۱۵۵ نویسه. ۹) ذخیره به‌صورتِ پیش‌نویس و ارسالِ لینکِ پیش‌نمایش.` },
  { kind: 'specific', title: 'متن دسته‌بندی محصول', use: 'دسته‌بندی محصول', steps: steps(['competitors', 'internal_links'], 3), body:
`متنِ توضیحاتِ دستهٔ محصول بنویس (فقط متن؛ دسته و محصولات از قبل وجود دارند). اول متنِ فعلیِ دسته را بخوان.
ساختار: پاراگرافِ کوتاهِ معرفی بالا؛ بعد H2هایی مثلِ انواع، کاربردها، راهنمای انتخاب/خرید، عواملِ مؤثر بر قیمت، سؤالات متداول.
لینکِ داخلی به زیردسته‌ها، محصولاتِ پرفروش و مقالاتِ راهنما. لحنِ فروش‌محور ولی صادق؛ قیمتِ عددی ننویس مگر بدهم.
ذخیره در خودِ دسته + عنوان/توضیحِ متا.` },
  { kind: 'specific', title: 'مقاله سریع', use: 'مقاله', steps: steps(['internal_links'], 0), body:
'مقالهٔ کوتاه (۶۰۰ تا ۹۰۰ کلمه) فقط بر اساسِ دانشِ خودت و موضوعی که می‌دهم؛ تحقیق لازم نیست. ۲ تا ۴ لینکِ داخلیِ مرتبط بده و پیش‌نویس کن.' },
];

export const DEFAULT_COMPETITORS = [
  { domain: 'digikala.com', kind: 'ignore', notes: 'فروشگاهِ عمومی' },
  { domain: 'torob.com', kind: 'ignore', notes: 'مقایسهٔ قیمت' },
];

export const DEFAULT_SETTINGS = { hl: 'fa', gl: 'ir', browser: 'chrome', headed: false, browserPath: '', proxy: '', insecure: false, maxChars: 20000 };
