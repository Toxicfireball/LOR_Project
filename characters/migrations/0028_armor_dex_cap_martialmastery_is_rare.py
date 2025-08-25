from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0027_armor_dex_cap'),
    ]

    operations = [
        # Keep state and DB in sync for Armor.dex_cap
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE characters_armor "
                    "ADD COLUMN IF NOT EXISTS dex_cap integer NULL;",
                    "ALTER TABLE characters_armor "
                    "DROP COLUMN IF EXISTS dex_cap;"
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='armor',
                    name='dex_cap',
                    field=models.IntegerField(
                        blank=True, null=True,
                        help_text='10 + dex cap for dodge'
                    ),
                ),
            ],
        ),

        # Keep state and DB in sync for MartialMastery.is_rare
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE characters_martialmastery "
                    "ADD COLUMN IF NOT EXISTS is_rare boolean NOT NULL DEFAULT false;",
                    "ALTER TABLE characters_martialmastery "
                    "DROP COLUMN IF EXISTS is_rare;"
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='martialmastery',
                    name='is_rare',
                    field=models.BooleanField(default=False, help_text='Mark this mastery as rare.'),
                ),
            ],
        ),
    ]
