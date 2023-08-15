# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-05-23 10:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emailtemplates', '0002_auto_20170428_1442'),
    ]

    operations = [
        migrations.CreateModel(
            name='MassEmailMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=255, verbose_name='subject')),
                ('content', models.TextField(verbose_name='content')),
                ('date_sent', models.DateTimeField(blank=True, null=True, verbose_name='sent')),
            ],
        ),
    ]
