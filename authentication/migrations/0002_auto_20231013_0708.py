# Generated by Django 3.0.14 on 2023-10-13 07:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authtoken',
            name='key_expires_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='authtoken',
            name='nonce_expires_at',
            field=models.DateTimeField(null=True),
        ),
    ]
