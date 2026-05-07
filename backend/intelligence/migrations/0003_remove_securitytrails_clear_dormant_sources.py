"""Drop SecurityTrails source choice and clear dormant HIBP/SecurityTrails rows.

SecurityTrails is being fully removed; HIBP is being disabled in the pipeline
(client/scaffolding kept for future re-enablement once a domain-verification
flow is built). Existing rows for both sources are deleted because the data
they contain is misleading or no longer relevant.
"""

from django.db import migrations, models


def delete_dormant_rows(apps, schema_editor):
    OsintResult = apps.get_model("intelligence", "OsintResult")
    SecuritySignal = apps.get_model("intelligence", "SecuritySignal")
    OsintResult.objects.filter(source__in=["hibp", "securitytrails"]).delete()
    SecuritySignal.objects.filter(source__in=["hibp", "securitytrails"]).delete()


def noop_reverse(apps, schema_editor):
    """Deleted rows can't be restored; reverse is a no-op."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("intelligence", "0002_securitysignal_source_osintresult"),
    ]

    operations = [
        migrations.RunPython(delete_dormant_rows, noop_reverse),
        migrations.AlterField(
            model_name="osintresult",
            name="source",
            field=models.CharField(
                choices=[
                    ("leakcheck", "Leakcheck"),
                    ("shodan", "Shodan"),
                    ("censys", "Censys"),
                    ("builtwith", "Builtwith"),
                    ("hibp", "Hibp"),
                ],
                max_length=50,
            ),
        ),
    ]
