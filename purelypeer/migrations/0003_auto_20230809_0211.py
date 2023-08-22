# Generated by Django 3.0.14 on 2023-08-09 02:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purelypeer', '0002_auto_20230808_0542'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashdropnftpair',
            name='key_category',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='cashdropnftpair',
            name='lock_category',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='vault',
            name='address',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='vault',
            name='token_address',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
