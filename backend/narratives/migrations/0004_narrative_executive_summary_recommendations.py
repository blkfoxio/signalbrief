from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("narratives", "0003_remove_narrative_business_impact_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="narrative",
            name="executive_summary",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="narrative",
            name="recommendations",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
