# Generated by Django 3.0.14 on 2023-07-28 04:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0057_auto_20230718_0630'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentmethod',
            name='deleted_at',
        ),
        migrations.RemoveField(
            model_name='paymentmethod',
            name='is_deleted',
        ),
    ]
