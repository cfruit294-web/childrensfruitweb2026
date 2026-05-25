from django.db import migrations, models


def approve_existing_users(apps, schema_editor):
    """Les comptes déjà existants sont approuvés automatiquement."""
    CustomUser = apps.get_model('core', 'CustomUser')
    CustomUser.objects.update(is_approved=True)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_customuser_country'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='phone',
            field=models.CharField(blank=True, max_length=20, verbose_name='Téléphone'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='google_id',
            field=models.CharField(blank=True, max_length=128, verbose_name='Google ID'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='is_approved',
            field=models.BooleanField(default=False, verbose_name='Approuvé par admin'),
        ),
        migrations.RunPython(approve_existing_users, migrations.RunPython.noop),
        migrations.CreateModel(
            name='PhoneVerificationCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('phone', models.CharField(max_length=20, verbose_name='Téléphone')),
                ('code', models.CharField(max_length=6)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_used', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Code OTP SMS',
                'verbose_name_plural': 'Codes OTP SMS',
                'ordering': ['-created_at'],
            },
        ),
    ]
