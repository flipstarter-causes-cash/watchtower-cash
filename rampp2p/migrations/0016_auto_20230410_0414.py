# Generated by Django 3.0.14 on 2023-04-10 04:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0015_feedback'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='arbiter',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='arbitrated_orders', to='rampp2p.Peer'),
        ),
        migrations.AlterField(
            model_name='order',
            name='creator',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='created_orders', to='rampp2p.Peer'),
        ),
    ]
