# Generated by Django 3.0.14 on 2023-09-06 03:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('paytacapos', '0012_auto_20230906_0254'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='merchant',
            name='signer_wallet_hash',
        ),
    ]
