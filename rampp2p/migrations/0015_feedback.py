# Generated by Django 3.0.14 on 2023-04-05 04:56

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0014_auto_20230404_0831'),
    ]

    operations = [
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('comment', models.CharField(blank=True, max_length=4000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('from_peer', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, to='rampp2p.Peer')),
                ('order', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='feedbacks', to='rampp2p.Order')),
                ('to_peer', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, to='rampp2p.Peer')),
            ],
        ),
    ]
