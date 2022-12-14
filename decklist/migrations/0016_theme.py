# Generated by Django 4.1.3 on 2023-01-02 13:12

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('decklist', '0015_make_cmdr_id_unique'),
    ]

    operations = [
        migrations.CreateModel(
            name='Theme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_name', models.CharField(help_text='Human-friendly theme name', max_length=30)),
                ('filter_text', models.CharField(help_text='String to match on cards', max_length=30)),
                ('filter_type', models.CharField(choices=[('T', 'tribal'), ('K', 'keyword')], max_length=1)),
                ('slug', models.SlugField(unique=True)),
                ('card_threshold', models.IntegerField(default=15, help_text='The minimum number of cards required in a deck to include it in the theme')),
                ('deck_threshold', models.SmallIntegerField(default=10, help_text="The fraction of a commander's decks with this theme in order to say the commander has that theme", validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
            ],
        ),
    ]
