from django.db import migrations


def map_armor_value(raw: int) -> int:
    if raw is None:
        return 0
    if raw <= 5:
        return 0
    if raw <= 12:
        return 1
    if raw <= 18:
        return 3
    if raw <= 26:
        return 4
    return 5  # 27+


def map_armor_defence(raw: int) -> int:
    if raw is None:
        return 0
    if raw <= 5:
        return 0
    if raw <= 10:
        return 1
    if raw <= 15:
        return 2
    if raw <= 20:
        return 3
    if raw <= 25:
        return 4
    return 5  # 26+


def forwards(apps, schema_editor):
    Armor = apps.get_model("characters", "Armor")

    qs = Armor.objects.all().only("id", "armor_value", "armor_defence")
    to_update = []

    for a in qs.iterator():
        raw = a.armor_value
        new_value = map_armor_value(raw)
        new_def = map_armor_defence(raw)

        if a.armor_value != new_value or a.armor_defence != new_def:
            a.armor_value = new_value
            a.armor_defence = new_def
            to_update.append(a)

    if to_update:
        Armor.objects.bulk_update(
            to_update,
            ["armor_value", "armor_defence"],
            batch_size=1000,
        )


def backwards(apps, schema_editor):
    # Not reversible: you overwrite the original raw armor_value.
    # If you need reversibility, you must add a "raw_armor_value" field first.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('characters', '0069_armor_armor_defence'),
    ]


    operations = [
        migrations.RunPython(forwards, backwards),
    ]
