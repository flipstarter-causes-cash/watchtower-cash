# Generated by Django 3.0.14 on 2023-05-25 08:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0041_recipient_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipient',
            name='address',
            field=models.CharField(max_length=200),
        ),
    ]
