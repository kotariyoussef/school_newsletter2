# Generated by Django 5.2 on 2025-04-19 11:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_studentprofile_bio'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='slug',
            field=models.SlugField(blank=True, unique=True),
        ),
    ]
