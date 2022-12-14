# Generated by Django 4.1.3 on 2022-12-25 16:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('decklist', '0009_card_partner_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='Commander',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('commander1', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='commander1_slots', to='decklist.card')),
                ('commander2', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='commander2_slots', to='decklist.card')),
            ],
        ),
        migrations.AddConstraint(
            model_name='commander',
            constraint=models.UniqueConstraint(condition=models.Q(('commander2__isnull', False)), fields=('commander1', 'commander2'), name='unique_pair_of_commanders', violation_error_message='Commander pair is not unique'),
        ),
        migrations.AddConstraint(
            model_name='commander',
            constraint=models.UniqueConstraint(condition=models.Q(('commander2__isnull', True)), fields=('commander1',), name='unique_single_commander', violation_error_message='Solo commander is not unique'),
        ),
        migrations.AddConstraint(
            model_name='commander',
            constraint=models.CheckConstraint(check=models.Q(('commander1_id__lte', models.F('commander2_id')), ('commander2__isnull', True), _connector='OR'), name='commander1_sorts_before_commander2', violation_error_message='Commander 1 ID must sort before commander 2 ID'),
        ),
    ]
