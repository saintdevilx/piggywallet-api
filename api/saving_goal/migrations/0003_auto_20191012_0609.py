# Generated by Django 2.2.6 on 2019-10-12 06:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('saving_goal', '0002_auto_20191011_0826'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='savinggoal',
            name='tags',
        ),
        migrations.AlterField(
            model_name='savinggoal',
            name='deleted_at',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.DeleteModel(
            name='Tagulous_SavingGoal_tags',
        ),
    ]
