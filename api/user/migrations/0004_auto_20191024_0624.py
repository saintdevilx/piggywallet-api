# Generated by Django 2.2.6 on 2019-10-24 06:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_bank_userbankaccount_userpaymentdetail'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='achieved_goal',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='in_progress_goal',
            field=models.IntegerField(default=0),
        ),
    ]