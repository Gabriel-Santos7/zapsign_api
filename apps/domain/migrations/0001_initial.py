from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Provider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('code', models.SlugField(max_length=50, unique=True)),
                ('api_base_url', models.URLField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'providers',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('api_token', models.CharField(max_length=500)),
                ('provider_config', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='companies', to='domain.provider')),
            ],
            options={
                'db_table': 'companies',
                'ordering': ['name'],
                'verbose_name_plural': 'companies',
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('open_id', models.CharField(blank=True, max_length=255, null=True)),
                ('token', models.CharField(blank=True, max_length=255, null=True)),
                ('provider_status', models.CharField(blank=True, max_length=50, null=True)),
                ('internal_status', models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending'), ('in_progress', 'In Progress'), ('signed', 'Signed'), ('cancelled', 'Cancelled'), ('rejected', 'Rejected'), ('expired', 'Expired')], default='draft', max_length=20)),
                ('file_url', models.URLField()),
                ('date_limit_to_sign', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='domain.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.User')),
            ],
            options={
                'db_table': 'documents',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Signer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('email', models.EmailField(max_length=254)),
                ('phone_country', models.CharField(blank=True, max_length=10, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=20, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('in_progress', 'In Progress'), ('signed', 'Signed'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('token', models.CharField(blank=True, max_length=255, null=True)),
                ('sign_url', models.URLField(blank=True, null=True)),
                ('external_id', models.CharField(blank=True, max_length=255, null=True)),
                ('auth_mode', models.CharField(blank=True, max_length=50, null=True)),
                ('times_viewed', models.IntegerField(default=0)),
                ('last_view_at', models.DateTimeField(blank=True, null=True)),
                ('signed_at', models.DateTimeField(blank=True, null=True)),
                ('resend_attempts', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signers', to='domain.document')),
            ],
            options={
                'db_table': 'signers',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='DocumentAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('missing_topics', models.JSONField(blank=True, default=list)),
                ('summary', models.TextField(blank=True)),
                ('insights', models.JSONField(blank=True, default=dict)),
                ('analyzed_at', models.DateTimeField(auto_now_add=True)),
                ('model_used', models.CharField(default='gpt-3.5-turbo', max_length=100)),
                ('document', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='analysis', to='domain.document')),
            ],
            options={
                'db_table': 'document_analyses',
                'verbose_name_plural': 'document analyses',
            },
        ),
    ]

