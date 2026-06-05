from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("questionnaires", "0008_responseset_suicide_risk_opt_in_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="responseset",
            index=models.Index(
                fields=["suicide_risk_triggered", "status"],
                name="idx_rs_suicide_risk_status",
            ),
        ),
    ]
