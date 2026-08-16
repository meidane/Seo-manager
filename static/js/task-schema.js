/* task-schema.js — منبع واحد «برچسب/رنگِ» انواعِ built-inِ عمومی (فنی/سایر)، فقط
   برای fallbackِ typeList() در tasks.js وقتی هنوز TaskTypeDef ای seed نشده. هرچیزِ
   تخصصی (سئو و…) دیگر اینجا نیست — فیلد سفارشیِ نوع تسک است (`TaskTypeDef.fields`،
   رندرِ داینامیک در tasks.js:renderCustom). برای افزودن نوعِ تخصصیِ جدید، به یک اپِ
   بستهٔ عمودی (مثل seo/) برو، نه اینجا. */
window.TASK_SCHEMA = {
  // برچسب و رنگ نوع تسکِ عمومیِ built-in (RGB) — با TYPE_COLORS در مدل هم‌خوان
  types: {
    tech: { label: 'فنی', rgb: '167,139,250' },
    other: { label: 'سایر', rgb: '143,160,184' },
  },
};
