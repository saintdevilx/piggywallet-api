# Generated by Django 2.2.6 on 2020-01-20 09:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0006_auto_20191230_1759'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentsubscription',
            name='status',
            field=models.SmallIntegerField(choices=[(1, 'ACTIVE'), (0, 'PENDING'), (2, 'CANCELLED')], default=0),
        ),
    ]