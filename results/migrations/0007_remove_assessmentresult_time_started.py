# Generated by Django 5.2 on 2025-07-13 16:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0006_assessmentresult_time_started'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='assessmentresult',
            name='time_started',
        ),
    ]
