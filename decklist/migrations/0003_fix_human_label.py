# Generated by Django 4.1.2 on 2022-10-31 01:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('decklist', '0002_basic_data_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deck',
            name='source',
            field=models.IntegerField(choices=[(0, 'Unknown/other'), (1, 'Archidekt')]),
        ),
    ]