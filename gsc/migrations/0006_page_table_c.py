# ۳/۳: حذفِ ستون‌های تکراری (آدرس در هر ردیف) + ایندکس‌های تازه.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('gsc', '0005_page_table_b')]

    operations = [
        migrations.RemoveIndex('gscqueryday', 'gsc_gscquer_site_id_bcbf57_idx'),
        migrations.RemoveIndex('gscqueryday', 'gsc_gscquer_site_id_909b64_idx'),
        migrations.RemoveIndex('gscqueryday', 'gsc_gscquer_site_id_a2cffa_idx'),
        migrations.RemoveIndex('gscpageday', 'gsc_gscpage_site_id_62a748_idx'),
        migrations.RemoveIndex('gscpageday', 'gsc_gscpage_site_id_6134d9_idx'),
        migrations.RemoveField('gscqueryday', 'old_page'),
        migrations.RemoveField('gscqueryday', 'page_key'),
        migrations.RemoveField('gscpageday', 'old_page'),
        migrations.RemoveField('gscpageday', 'page_key'),
        migrations.AlterField('gscqueryday', 'page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='gsc.gscpage')),
        migrations.AlterField('gscpageday', 'page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='gsc.gscpage')),
        migrations.AddIndex('gscqueryday', models.Index(fields=['page', 'date'], name='gsc_qday_page_date')),
        migrations.AddIndex('gscqueryday', models.Index(fields=['site', 'date'], name='gsc_qday_site_date')),
        migrations.AddIndex('gscpageday', models.Index(fields=['page', 'date'], name='gsc_pday_page_date')),
        migrations.AddIndex('gscpageday', models.Index(fields=['site', 'date'], name='gsc_pday_site_date')),
    ]
