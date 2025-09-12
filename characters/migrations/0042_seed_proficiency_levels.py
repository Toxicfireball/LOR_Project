# characters/migrations/0042_seed_proficiency_levels.py
from django.db import migrations

def seed(apps, schema_editor):
    ProficiencyLevel = apps.get_model("characters", "ProficiencyLevel")

    # name, bonus, tier_index
    data = [
        ("Untrained",  0, 0),
        ("Trained",    2, 1),
        ("Expert",     5, 2),
        ("Master",     8, 3),
        ("Legendary", 12, 4),
    ]

    # Be defensive in case older states didn’t have `tier` yet.
    field_names = {f.name for f in ProficiencyLevel._meta.local_fields}
    has_tier = "tier" in field_names

    for name, bonus, tier in data:
        defaults = {"bonus": bonus}
        if has_tier:
            defaults["tier"] = tier
        # ensure we *set* tier/bonus even if the row already exists
        ProficiencyLevel.objects.update_or_create(
            name=name,
            defaults=defaults,
        )

class Migration(migrations.Migration):
    dependencies = [
        ("characters", "0041_remove_classproficiencyprogress_cpp_unique_generic_per_level_and_more"),
    ]
    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
