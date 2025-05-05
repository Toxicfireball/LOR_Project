# characters/migrations/0043_split_feature_type.py
from django.db import migrations, models

def copy_feature_type(apps, schema_editor):
    CF = apps.get_model('characters', 'ClassFeature')
    for feat in CF.objects.all():
        old = feat.feature_type
        # map old → scope
        if old == 'subclass_feat':
            feat.scope = 'subclass_feat'
        elif old == 'subclass_choice':
            feat.scope = 'subclass_choice'
        else:
            feat.scope = 'class_feat'
        # map old → kind
        if old in ('class_feat', 'skill_feat', 'martial_mastery', 'modify_proficiency', 'spell_table'):
            feat.kind = old
        else:
            feat.kind = 'class_feat'
        feat.save()

def undo_copy(apps, schema_editor):
    CF = apps.get_model('characters', 'ClassFeature')
    for feat in CF.objects.all():
        # reconstruct feature_type from kind or scope
        if feat.kind in ('class_feat', 'skill_feat', 'martial_mastery', 'modify_proficiency', 'spell_table'):
            feat.feature_type = feat.kind
        else:
            feat.feature_type = feat.scope or 'class_feat'
        feat.save()

class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0042_alter_classfeature_modify_proficiency_amount'),
    ]

    operations = [
        # 1) Add new, nullable fields
        migrations.AddField(
            model_name='classfeature',
            name='scope',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('class_feat', 'Class Feature'),
                    ('subclass_feat', 'Subclass Feature'),
                    ('subclass_choice', 'Subclass Choice'),
                ],
                null=True,
                blank=True,
                help_text='Does this belong to the base class, a subclass, or is it a subclass-choice?',
            ),
        ),
        migrations.AddField(
            model_name='classfeature',
            name='kind',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('class_feat', 'Class Feat'),
                    ('skill_feat', 'Skill Feat'),
                    ('martial_mastery', 'Martial Mastery'),
                    ('modify_proficiency', 'Modify Proficiency'),
                    ('spell_table', 'Spell Slot Table'),
                ],
                null=True,
                blank=True,
                help_text='What *type* of feature this is.',
            ),
        ),

        # 2) Copy existing feature_type → scope + kind
        migrations.RunPython(copy_feature_type, reverse_code=undo_copy),

        # 3) Make the new fields non-nullable (optional)
        migrations.AlterField(
            model_name='classfeature',
            name='scope',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('class_feat', 'Class Feature'),
                    ('subclass_feat', 'Subclass Feature'),
                    ('subclass_choice', 'Subclass Choice'),
                ],
                help_text='Does this belong to the base class, a subclass, or is it a subclass-choice?',
            ),
        ),
        migrations.AlterField(
            model_name='classfeature',
            name='kind',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('class_feat', 'Class Feat'),
                    ('skill_feat', 'Skill Feat'),
                    ('martial_mastery', 'Martial Mastery'),
                    ('modify_proficiency', 'Modify Proficiency'),
                    ('spell_table', 'Spell Slot Table'),
                ],
                help_text='What *type* of feature this is.',
            ),
        ),

        # 4) Remove the old feature_type field
        migrations.RemoveField(
            model_name='classfeature',
            name='feature_type',
        ),
    ]

