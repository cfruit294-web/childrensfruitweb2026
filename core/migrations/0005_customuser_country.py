from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_videocontent_youtube_url_textfield'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='country',
            field=models.CharField(blank=True, max_length=100, verbose_name="Pays d'origine"),
        ),
    ]
