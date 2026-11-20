# ۱/۳: جدولِ صفحه + FKِ خالی (فیلدهای قدیمی موقتاً می‌مانند). هر مرحله تراکنشِ جدا (Postgres: pending trigger events).
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('gsc', '0003_gscaccount_relay_key_gscaccount_relay_url')]

    operations = [
        migrations.CreateModel(
            name='GSCPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=700)),
                ('url', models.CharField(max_length=1000)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pages', to='gsc.gscsite')),
            ],
            options={'unique_together': {('site', 'key')}},
        ),
        migrations.RenameField('gscqueryday', 'page', 'old_page'),
        migrations.RenameField('gscpageday', 'page', 'old_page'),
        migrations.AddField('gscqueryday', 'page', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='gsc.gscpage')),
        migrations.AddField('gscpageday', 'page', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='gsc.gscpage')),
    ]
