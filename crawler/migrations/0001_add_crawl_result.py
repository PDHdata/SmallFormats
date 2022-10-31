# Generated by Django 4.1.2 on 2022-10-31 01:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('decklist', '0003_fix_human_label'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeckCrawlResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('crawl_time', models.DateTimeField()),
                ('url', models.URLField()),
                ('updated_time', models.DateTimeField()),
                ('got_cards', models.BooleanField(default=False)),
                ('deck', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='decklist.deck')),
            ],
        ),
    ]
