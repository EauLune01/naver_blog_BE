# Generated by Django 5.1 on 2025-02-07 08:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0020_heart_is_read'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='category',
            field=models.CharField(default='게시판', max_length=50),
        ),
    ]
