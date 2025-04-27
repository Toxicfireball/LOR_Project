from django.db import migrations
from django.db import models            # add this import at the top
def copy_type_to_group(apps, schema_editor):
    Group      = apps.get_model("characters", "SubclassGroup")
    Subclass   = apps.get_model("characters", "ClassSubclass")

    for grp in Group.objects.all():
        # fetch distinct types among children
        types = (
            Subclass.objects.filter(group_id=grp.id)
                            .values_list("system_type", flat=True)
                            .distinct()
        )
        if types:
            # pick the first (or assert they are identical)
            grp.system_type = types[0]
            grp.save(update_fields=["system_type"])

class Migration(migrations.Migration):
    dependencies = [
        ("characters", "0027_alter_subclassgroup_options_and_more"),
    ]
    operations = [
migrations.AddField(
    model_name="subclassgroup",
    name="system_type",
    field=models.CharField(              # ← correct
        max_length=20,
        choices=[
            ("linear",          "Linear"),
            ("modular_linear",  "Modular Linear"),
            ("modular_mastery", "Modular Mastery"),
        ],
        default="linear",
    ),
),
        migrations.RunPython(copy_type_to_group, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="classsubclass",
            name="system_type",
        ),
    ]
