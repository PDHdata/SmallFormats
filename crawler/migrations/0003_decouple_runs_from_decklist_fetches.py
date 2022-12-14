# Generated by Django 4.1.2 on 2022-11-12 21:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crawler', '0002_make_crawl_resumable'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deckcrawlresult',
            name='run',
        ),
        migrations.AddField(
            model_name='deckcrawlresult',
            name='target',
            field=models.IntegerField(choices=[(0, 'Unknown/other'), (1, 'Archidekt')], default=0),
        ),
        migrations.AlterField(
            model_name='crawlrun',
            name='state',
            field=models.IntegerField(choices=[(0, 'Not Started'), (1, 'Fetching Decks'), (5, 'Complete'), (98, 'Cancelled'), (99, 'Error')]),
        ),
    ]
