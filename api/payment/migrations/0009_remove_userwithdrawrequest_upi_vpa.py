# Generated by Django 2.2.6 on 2020-05-05 07:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0008_auto_20200331_0733'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userwithdrawrequest',
            name='upi_vpa',
        ),
    ]
