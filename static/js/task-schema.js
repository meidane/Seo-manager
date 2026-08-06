/* task-schema.js — منبع واحد «کدام فیلد برای کدام نوع تسک».
   هم مودال (نمایش/مخفی کردن فیلدها) و هم منطق فرانت از همین می‌خوانند.
   مطابق جدول بخش ۴.۳ سند. برای افزودن فیلد جدید فقط اینجا و مدل را تغییر بده. */
window.TASK_SCHEMA = {
  // گروه‌های فیلد و اینکه هر گروه برای کدام نوع‌ها فعال است
  groups: {
    content: { // تعداد کلمه، کلمات کلیدی، LSI، عنوان سئو، جایگاه، لینک انتشار
      fields: ['word_count', 'keywords', 'lsi_keywords', 'seo_title', 'current_rank', 'target_rank', 'published_url'],
      types: ['publish', 'update', 'reportage'],
    },
    update_only: { fields: ['source_url'], types: ['update'] },
    reportage: { fields: ['media_name', 'media_cost'], types: ['reportage'] },
    anchor: { fields: ['anchor_text', 'target_url'], types: ['reportage', 'linkbuilding'] },
    link: { fields: ['link_type', 'link_count'], types: ['linkbuilding'] },
    review: { fields: ['review_block'], types: ['publish', 'update', 'reportage'] },
    subtype: { fields: ['update_type'], types: ['update'] }, // سطحی/اساسی
  },

  // برچسب و رنگ نوع تسک (RGB) — با مدل هم‌خوان
  types: {
    publish: { label: 'انتشار', rgb: '56,189,248' },
    update: { label: 'آپدیت', rgb: '251,191,36' },
    tech: { label: 'فنی', rgb: '167,139,250' },
    reportage: { label: 'رپورتاژ', rgb: '244,114,182' },
    linkbuilding: { label: 'لینک‌سازی', rgb: '45,212,167' },
    other: { label: 'سایر', rgb: '143,160,184' },
  },

  /** فهرست فیلدهایی که برای یک نوع باید دیده شوند. */
  fieldsFor(type, updateType) {
    const on = new Set();
    for (const g of Object.values(this.groups)) {
      if (g.types.includes(type)) g.fields.forEach((f) => on.add(f));
    }
    // آپدیت اساسی رنگ نارنجی می‌گیرد (فقط نمایشی)
    return on;
  },
};
