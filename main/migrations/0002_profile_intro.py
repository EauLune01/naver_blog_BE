# Generated by Django 5.1 on 2025-01-27 07:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='intro',
            field=models.CharField(blank=True, help_text='간단한 자기소개를 입력해주세요 (최대 100자)', max_length=100, null=True),
        ),
    ]