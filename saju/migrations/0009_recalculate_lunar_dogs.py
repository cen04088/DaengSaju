from django.db import migrations


def clear_lunar_dog_results(apps, schema_editor):
    """이전 버전은 음력 생일을 양력으로 잘못 계산했으므로, 음력 강아지의 결과 캐시를 지워 다시 계산되게 합니다."""
    Dog = apps.get_model('saju', 'Dog')
    lunar_dog_ids = list(Dog.objects.filter(is_lunar=True).values_list('id', flat=True))
    if not lunar_dog_ids:
        return
    for model_name in ('SajuBasics', 'AIInterpretation', 'DailyWalkingLuck', 'Compatibility'):
        apps.get_model('saju', model_name).objects.filter(dog_id__in=lunar_dog_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('saju', '0008_dog_leap_month_share_token'),
    ]

    operations = [
        migrations.RunPython(clear_lunar_dog_results, migrations.RunPython.noop),
    ]
