# Generated by Django 4.1.2 on 2022-11-01 15:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('decklist', '0005_card_vs_printing'),
    ]

    operations = [
        migrations.AddField(
            model_name='printing',
            name='set_code',
            field=models.CharField(blank=True, max_length=5),
        ),
    ]
