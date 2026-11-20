"""خروجیِ اکسلِ سرچ کنسول (openpyxl): تبِ پروژه = یک شیت برای هر بخش؛ کارتِ تسک = کلماتِ صفحه + روندِ روزانه.
همان دادهٔ `analysis.py` (منطقِ موازی ندارد). شیت‌ها راست‌به‌چپ، سرستونِ پررنگ، عرضِ ستون خودکار."""
from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from . import analysis

HEAD = Font(bold=True)
FILL = PatternFill('solid', fgColor='E8EAF6')


def _sheet(wb, title, cols, rows):
    ws = wb.create_sheet(title[:31])
    ws.sheet_view.rightToLeft = True
    ws.append(cols)
    for c in ws[1]:
        c.font, c.fill = HEAD, FILL
    for r in rows:
        ws.append(list(r))
    for i, col in enumerate(ws.columns, 1):
        w = max((len(str(c.value or '')) for c in col), default=8)
        ws.column_dimensions[col[0].column_letter].width = min(max(10, w + 2), 70)
    ws.freeze_panes = 'A2'
    return ws


def _response(wb, name):
    if 'Sheet' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Sheet']
    buf = BytesIO()
    wb.save(buf)
    r = HttpResponse(buf.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    r['Content-Disposition'] = f"attachment; filename*=UTF-8''{__import__('urllib.parse').parse.quote(name)}.xlsx"
    return r


def project_xlsx(project):
    wb = Workbook()
    d = analysis.project_analysis(project)
    if not d:
        _sheet(wb, 'خالی', ['پیام'], [['این پروژه به سرچ کنسول وصل نیست یا هنوز همگام نشده']])
        return _response(wb, f'gsc-{project.pk}')
    c, p = d['total']['current'], d['total']['previous']
    _sheet(wb, 'خلاصه', ['معیار', '۲۸ روزِ اخیر', '۲۸ روزِ قبل'],
           [['کلیک', c['clicks'], p['clicks']], ['ایمپرشن', c['impressions'], p['impressions']],
            ['CTR %', c['ctr'], p['ctr']], ['جایگاه', c['position'], p['position']], ['داده تا', d['until'], '']])
    _sheet(wb, 'روند روزانه', ['تاریخ', 'کلیک', 'ایمپرشن', 'CTR %', 'جایگاه'],
           [[x['date'], x['clicks'], x['impressions'], x['ctr'], x['position']] for x in d['series']])
    _sheet(wb, 'افت صفحه‌ها', ['صفحه', 'کلیک قبل', 'کلیک اخیر', 'افت %', 'جایگاه قبل', 'جایگاه اخیر'],
           [[x['page'], x['before']['clicks'], x['after']['clicks'], x['drop'], x['before']['position'], x['after']['position']] for x in d['decline']])
    _sheet(wb, 'نزدیک صفحه اول', ['کلمه', 'صفحه', 'ایمپرشن', 'کلیک', 'جایگاه'],
           [[x['query'], x['page'], x['impressions'], x['clicks'], x['position']] for x in d['striking']])
    _sheet(wb, 'CTR پایین', ['کلمه', 'صفحه', 'جایگاه', 'ایمپرشن', 'CTR %'],
           [[x['query'], x['page'], x['position'], x['impressions'], x['ctr']] for x in d['low_ctr']])
    _sheet(wb, 'رقابت صفحه‌ها', ['کلمه', 'صفحه', 'ایمپرشن', 'کلیک', 'جایگاه'],
           [[x['query'], pg['page'], pg['impressions'], pg['clicks'], pg['position']] for x in d['cannibal'] for pg in x['pages']])
    ch = d['changes']
    _sheet(wb, 'کلمات تازه', ['کلمه', 'ایمپرشن', 'کلیک', 'جایگاه'], [[x['query'], x['impressions'], x['clicks'], x['position']] for x in ch['new']])
    _sheet(wb, 'کلمات ازدست‌رفته', ['کلمه', 'ایمپرشنِ قبل', 'کلیکِ قبل', 'جایگاهِ قبل'],
           [[x['query'], x['impressions'], x['clicks'], x['position']] for x in ch['lost']])
    _sheet(wb, 'جابه‌جایی جایگاه', ['کلمه', 'جایگاه قبل', 'جایگاه اخیر', 'تغییر (+ بهتر)', 'ایمپرشن'],
           [[x['query'], x['before'], x['after'], x['delta'], x['impressions']] for x in ch['up'] + ch['down']])
    _sheet(wb, 'بخش‌های سایت', ['بخش', 'صفحه‌ها', 'کلیک قبل', 'کلیک اخیر', 'ایمپرشن قبل', 'ایمپرشن اخیر', 'جایگاه قبل', 'جایگاه اخیر'],
           [[x['section'], x['pages'], x['previous']['clicks'], x['current']['clicks'], x['previous']['impressions'],
             x['current']['impressions'], x['previous']['position'], x['current']['position']] for x in d['sections']])
    _sheet(wb, 'دستگاه‌ها', ['دستگاه', 'کلیک قبل', 'کلیک اخیر', 'ایمپرشن قبل', 'ایمپرشن اخیر', 'جایگاه قبل', 'جایگاه اخیر'],
           [[x['device'], x['previous']['clicks'], x['current']['clicks'], x['previous']['impressions'], x['current']['impressions'],
             x['previous']['position'], x['current']['position']] for x in d['devices']])
    if d['index']:
        _sheet(wb, 'ایندکس نشده', ['صفحه', 'عنوان', 'وضعیت', 'آخرین کراول', 'بررسی'],
               [[x['url'], x['title'], x['coverage'], x['last_crawl'], x['checked']] for x in d['index']['not_indexed']])
    un = analysis.unseen_pages(project, limit=100000)
    if un['rows']:
        _sheet(wb, 'صفحه‌های بی‌نمایش', ['صفحه', 'عنوان', 'نوع', 'انتشار', 'ایندکس'],
               [[x['url'], x['title'], x['kind'], x['published'], ('بله' if x['index']['indexed'] else x['index']['coverage']) if x['index'] else '']
                for x in un['rows']])
    _sheet(wb, 'اثر کارها', ['تسک', 'نوع', 'تاریخ', 'روز', 'کلیک قبل', 'کلیک بعد', 'تغییر کلیک', 'تغییر جایگاه (+ بهتر)', 'هزینه/کلیک'],
           [[w['title'], w['type'], w['done'], w['days'], w['clicks_before'], w['clicks_after'], w['clicks_delta'], w['position_delta'],
             w['cost_per_click']] for w in d['work']])
    return _response(wb, f'search-console-{project.name}')


def task_xlsx(task):
    wb = Workbook()
    for i, p in enumerate(analysis.task_card(task), 1):
        sfx = f' {i}' if i > 1 else ''
        _sheet(wb, f'کلمات{sfx}', ['کلمه', 'کلیک', 'ایمپرشن', 'CTR %', 'جایگاه'],
               [[q['query'], q['clicks'], q['impressions'], q['ctr'], q['position']] for q in p['queries']])
        _sheet(wb, f'روند{sfx}', ['تاریخ', 'کلیک', 'ایمپرشن', 'CTR %', 'جایگاه'],
               [[x['date'], x['clicks'], x['impressions'], x['ctr'], x['position']] for x in p['series']])
    if len(wb.sheetnames) == 1:
        _sheet(wb, 'خالی', ['پیام'], [['برای صفحهٔ این تسک داده‌ای در سرچ کنسول نیست']])
    return _response(wb, f'task-{task.pk}-search-console')
