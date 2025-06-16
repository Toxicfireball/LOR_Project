# characters/migrations/0005_move_subskill_to_skill.py
from django.db import migrations, models

def forwards(apps, schema_editor):
    SubSkill = apps.get_model("characters", "SubSkill")
    Skill    = apps.get_model("characters", "Skill")
    for ss in SubSkill.objects.all():
        cat = getattr(ss, "category", None)
        if cat:
            try:
                # assume your Skill.name == old SkillCategory.name
                sk = Skill.objects.get(name=cat.name)
            except Skill.DoesNotExist:
                continue
            ss.skill = sk
            ss.save(update_fields=["skill"])

class Migration(migrations.Migration):

    dependencies = [
        ('characters',
         '0005_skill_description_subskill_description_and_more'),
    ]


    operations = [
        # 1) add the new FK, allow NULL so we can backfill
        migrations.AddField(
            model_name="subskill",
            name="skill",
            field=models.ForeignKey(
                to="characters.Skill",
                null=True,
                on_delete=models.CASCADE,
                related_name="subskills",
            ),
        ),
        # 2) backfill data
        migrations.RunPython(forwards, migrations.RunPython.noop),
        # 3) now make it non-nullable
        migrations.AlterField(
            model_name="subskill",
            name="skill",
            field=models.ForeignKey(
                to="characters.Skill",
                on_delete=models.CASCADE,
                related_name="subskills",
            ),
        ),
        # 4) drop the old category field
        migrations.RemoveField("subskill", "category"),
        # 5) delete the SkillCategory model
        migrations.DeleteModel("SkillCategory"),
    ]
