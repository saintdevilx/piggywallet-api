# Generated by Django 2.2.6 on 2020-07-04 06:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reward', '0006_auto_20200701_0515'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='slug',
            field=models.SlugField(blank=True),
        ),
    ]
