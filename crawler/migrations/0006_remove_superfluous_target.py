# Generated by Django 4.1.2 on 2022-11-27 17:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crawler', '0005_deckcrawlresult_fetchable'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deckcrawlresult',
            name='target',
        ),
    ]
