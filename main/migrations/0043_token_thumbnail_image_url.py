# Generated by Django 3.0.14 on 2021-09-22 07:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0042_auto_20210911_0141'),
    ]

    operations = [
        migrations.AddField(
            model_name='token',
            name='thumbnail_image_url',
            field=models.URLField(blank=True),
        ),
    ]
