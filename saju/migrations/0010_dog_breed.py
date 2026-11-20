from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('saju', '0009_recalculate_lunar_dogs'),
    ]

    operations = [
        migrations.AddField(
            model_name='dog',
            name='breed',
            field=models.CharField(blank=True, default='', max_length=40, verbose_name='품종'),
        ),
    ]
