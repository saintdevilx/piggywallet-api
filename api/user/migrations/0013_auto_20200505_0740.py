# Generated by Django 2.2.6 on 2020-05-05 07:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0012_auto_20200206_1153'),
    ]

    operations = [
        migrations.AddField(
            model_name='userbankaccount',
            name='upi_vpa',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='userbankaccount',
            name='account_holder_name',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='userbankaccount',
            name='account_no',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='userbankaccount',
            name='bank',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.Bank'),
        ),
        migrations.AlterField(
            model_name='userbankaccount',
            name='ifsc_code',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.CreateModel(
            name='VirtualAccount',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('deleted_at', models.DateTimeField(blank=True, default=None, null=True)),
                ('account_id', models.CharField(max_length=50, null=True)),
                ('account_vpa_id', models.CharField(max_length=50, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
