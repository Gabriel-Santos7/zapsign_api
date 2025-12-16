from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('domain', '0002_seed_zapsign_provider'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='signer',
            name='phone_country',
        ),
        migrations.RemoveField(
            model_name='signer',
            name='phone_number',
        ),
        migrations.RemoveField(
            model_name='signer',
            name='external_id',
        ),
        migrations.RemoveField(
            model_name='signer',
            name='auth_mode',
        ),
        migrations.RemoveField(
            model_name='signer',
            name='times_viewed',
        ),
        migrations.RemoveField(
            model_name='signer',
            name='last_view_at',
        ),
        migrations.RemoveField(
            model_name='signer',
            name='signed_at',
        ),
        migrations.RemoveField(
            model_name='signer',
            name='resend_attempts',
        ),
    ]

