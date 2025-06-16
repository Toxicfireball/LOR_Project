# characters/migrations/000X_normalize_skill_ability.py
from django.db import migrations

CODE_MAP = {
    "STR": "strength",
    "DEX": "dexterity",
    "CON": "constitution",
    "INT": "intelligence",
    "WIS": "wisdom",
    "CHA": "charisma",
}

def forwards(apps, schema_editor):
    Skill = apps.get_model("characters", "Skill")
    for s in Skill.objects.all():
        s.ability = CODE_MAP.get(s.ability.upper(), "strength")
        s.save(update_fields=["ability"])

class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0003_loremasterimage_loremasterarticle'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
