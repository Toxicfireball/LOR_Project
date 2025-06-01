# characters/migrations/0008_add_unlock_and_min_levels.py

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("characters", "0007_alter_subclasstierlevel_unique_together_and_more"),
    ]

    operations = [
        # A) Add the new unlock_level field to SubclassTierLevel
        migrations.AddField(
            model_name="subclasstierlevel",
            name="unlock_level",
            field=models.PositiveIntegerField(
                help_text="Class‐level at which this tier becomes available.",
                null=True,
            ),
        ),
        # B) Now that unlock_level exists, add the new unique_together
        migrations.AlterUniqueTogether(
            name="subclasstierlevel",
            unique_together={
                ("subclass_group", "tier"),
                ("subclass_group", "unlock_level"),
            },
        ),
        # C) Add the new min_level field to ClassFeature
        migrations.AddField(
            model_name="classfeature",
            name="min_level",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="(Optional) extra minimum class‐level required to pick this feature, beyond tier mapping.",
                null=True,
            ),
        ),
    ]
