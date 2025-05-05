# characters/migrations/0042_rebuild_modify_proficiency_amount.py
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("characters", "0041_alter_classfeature_action_type"),
    ]

    operations = [
        # 1) drop the old CharField column entirely
        migrations.RemoveField(
            model_name="classfeature",
            name="modify_proficiency_amount",
        ),

        # 2) add it back as a nullable FK
        migrations.AddField(
            model_name="classfeature",
            name="modify_proficiency_amount",
            field=models.ForeignKey(
                to="characters.ProficiencyTier",
                null=True,
                blank=True,
                on_delete=models.SET_NULL,
                help_text="Pick the exact proficiency tier to grant (overrides current tier)",
            ),
        ),
    ]
