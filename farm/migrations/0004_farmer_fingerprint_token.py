# Generated by Django 4.2 on 2024-10-08 03:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("farm", "0003_produce_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmer",
            name="fingerprint_token",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
