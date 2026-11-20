# ۲/۳: انتقالِ داده — صفحه‌های یکتا از هر دو جدول + پرکردنِ FK با یک UPDATE ... FROM (Postgres و SQLite ≥3.33). بدونِ از دست رفتنِ داده.
from django.db import migrations


def forward(apps, schema_editor):
    Page = apps.get_model('gsc', 'GSCPage')
    Q = apps.get_model('gsc', 'GSCQueryDay')
    P = apps.get_model('gsc', 'GSCPageDay')
    pt, qt, ptd = Page._meta.db_table, Q._meta.db_table, P._meta.db_table
    with schema_editor.connection.cursor() as c:
        c.execute(f'''INSERT INTO {pt} (site_id, key, url)
                      SELECT site_id, page_key, MIN(old_page) FROM (
                        SELECT site_id, page_key, old_page FROM {qt} UNION ALL SELECT site_id, page_key, old_page FROM {ptd}) x
                      GROUP BY site_id, page_key''')
        for t in (qt, ptd):
            c.execute(f'UPDATE {t} SET page_id = p.id FROM {pt} p WHERE p.site_id = {t}.site_id AND p.key = {t}.page_key')


class Migration(migrations.Migration):
    dependencies = [('gsc', '0004_page_table_a')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
