# Generated by Django 4.1.2 on 2022-11-27 17:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('decklist', '0007_add_moxfield'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('legal_decks', models.IntegerField()),
            ],
            options={
                'get_latest_by': 'timestamp',
            },
        ),
    ]
