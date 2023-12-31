# Generated by Django 2.2.6 on 2019-11-06 12:45

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_auto_20191024_0624'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='kyc_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='UserKYCDetail',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('deleted_at', models.DateTimeField(default=None, null=True)),
                ('pan_no', models.CharField(max_length=20)),
                ('pan_image', models.CharField(max_length=500)),
                ('adhaar_no', models.CharField(max_length=20)),
                ('adhaar_image', models.CharField(max_length=500)),
                ('user_photo', models.CharField(max_length=500)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
