# Generated by Django 2.2.6 on 2020-07-01 05:15

import api.saving_goal.utils
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reward', '0005_auto_20200701_0505'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='reward',
            options={'ordering': ('-created_at',)},
        ),
        # migrations.AlterField(
        #     model_name='reward',
        #     name='reward_id',
        #     field=models.CharField(default=api.saving_goal.utils.current_timestamp_string, max_length=20, null=True, unique=True),
        # ),
    ]
