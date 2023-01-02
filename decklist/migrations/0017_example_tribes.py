# Generated by Django 4.1.3 on 2023-01-02 13:24

from django.db import migrations


def add_sample_themes(apps, schema_editor):
    Theme = apps.get_model('decklist', 'Theme')
    # note: filter_type='T' corresponds to Theme.Type.TRIBE
    Theme.objects.bulk_create(
        [
            Theme(display_name='Angel', filter_text='Angel', slug='angel', filter_type='T'),
            Theme(display_name='Bird', filter_text='Bird', slug='bird', filter_type='T'),
            Theme(display_name='Dragon', filter_text='Dragon', slug='dragon', filter_type='T'),
            Theme(display_name='Druid', filter_text='Druid', slug='druid', filter_type='T'),
            Theme(display_name='Elf', filter_text='Elf', slug='elf', filter_type='T'),
            Theme(display_name='Goblin', filter_text='Goblin', slug='goblin', filter_type='T'),
            Theme(display_name='Human', filter_text='Human', slug='human', filter_type='T'),
            Theme(display_name='Knight', filter_text='Knight', slug='knight', filter_type='T'),
            Theme(display_name='Merfolk', filter_text='Merfolk', slug='merfolk', filter_type='T'),
            Theme(display_name='Pirate', filter_text='Pirate', slug='pirate', filter_type='T'),
            Theme(display_name='Rogue', filter_text='Rogue', slug='rogue', filter_type='T'),
            Theme(display_name='Sliver', filter_text='Sliver', slug='sliver', filter_type='T'),
            Theme(display_name='Spirit', filter_text='Spirit', slug='spirit', filter_type='T'),
            Theme(display_name='Vampire', filter_text='Vampire', slug='vampire', filter_type='T'),
            Theme(display_name='Warrior', filter_text='Warrior', slug='warrior', filter_type='T'),
            Theme(display_name='Wizard', filter_text='Wizard', slug='wizard', filter_type='T'),
            Theme(display_name='Zombie', filter_text='Zombie', slug='zombie', filter_type='T'),
        ],
        ignore_conflicts=True,
    )

class Migration(migrations.Migration):

    dependencies = [
        ('decklist', '0016_theme'),
    ]

    operations = [
        migrations.RunPython(add_sample_themes, migrations.RunPython.noop),
    ]
