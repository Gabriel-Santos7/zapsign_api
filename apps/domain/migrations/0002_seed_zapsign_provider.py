from django.db import migrations


def create_zapsign_provider(apps, schema_editor):
    Provider = apps.get_model('domain', 'Provider')
    Provider.objects.get_or_create(
        code='zapsign',
        defaults={
            'name': 'ZapSign',
            'api_base_url': 'https://sandbox.api.zapsign.com.br',
            'is_active': True,
        }
    )


def reverse_create_zapsign_provider(apps, schema_editor):
    Provider = apps.get_model('domain', 'Provider')
    Provider.objects.filter(code='zapsign').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('domain', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_zapsign_provider, reverse_create_zapsign_provider),
    ]


