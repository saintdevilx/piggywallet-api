# Generated by Django 2.2.6 on 2019-10-12 06:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('saving_goal', '0003_auto_20191012_0609'),
    ]

    operations = [
        migrations.AlterField(
            model_name='savinggoal',
            name='target_date',
            field=models.DateTimeField(default=None, null=True),
        ),
    ]