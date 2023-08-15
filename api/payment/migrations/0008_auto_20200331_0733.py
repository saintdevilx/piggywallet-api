# Generated by Django 2.2.6 on 2020-03-31 07:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0007_auto_20200120_0921'),
    ]

    operations = [
        migrations.AddField(
            model_name='userwithdrawrequest',
            name='upi_vpa',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='userwithdrawrequest',
            name='user_bank_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='user.UserBankAccount'),
        ),
    ]
