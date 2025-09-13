# characters/migrations/0045_fix_race_subrace_fk_types.py
from django.db import migrations

SQL_STAGE1 = r"""
-- Stage 1: create/compute bigint column and purge bad rows + dependents

-- 1) Build the new BIGINT column (idempotent)
ALTER TABLE characters_character
  ADD COLUMN IF NOT EXISTS subrace_id_new BIGINT;

-- 2) Map text codes -> ids
UPDATE characters_character c
SET subrace_id_new = s.id
FROM characters_subrace s
WHERE c.subrace_id = s.code;

-- 3) Coerce numeric strings (if any)
UPDATE characters_character
SET subrace_id_new = NULLIF(subrace_id,'')::BIGINT
WHERE subrace_id_new IS NULL AND subrace_id ~ '^[0-9]+$';

-- 4) Delete dependents for characters whose subrace didn't resolve
--    (i.e., they had a non-empty subrace_id, but we still couldn't map it)
DELETE FROM characters_characterclassprogress WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characterfeature WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characterfeat WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characterskillproficiency WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characterskillrating WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_charactersubskillproficiency WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characterweaponequip WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characterknownspell WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characterpreparedspell WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_charactermanualgrant WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characterfieldoverride WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characterfieldnote WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characterresource WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_charactermartialmastery WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characteractivation WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
DELETE FROM characters_characterskillpointtx WHERE character_id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);

-- 5) Delete the characters themselves
DELETE FROM characters_character
WHERE id IN (
  SELECT id FROM characters_character
  WHERE subrace_id IS NOT NULL AND subrace_id <> '' AND subrace_id_new IS NULL
);
"""

SQL_STAGE2 = r"""
-- Stage 2: swap in the bigint column and add the FK (separate transaction)

-- Make sure no previous partially-created FK remains
ALTER TABLE characters_character
  DROP CONSTRAINT IF EXISTS characters_character_subrace_id_fkey;

-- Swap columns
ALTER TABLE characters_character RENAME COLUMN subrace_id    TO subrace_id_old;
ALTER TABLE characters_character RENAME COLUMN subrace_id_new TO subrace_id;

-- Real FK
ALTER TABLE characters_character
  ADD CONSTRAINT characters_character_subrace_id_fkey
  FOREIGN KEY (subrace_id) REFERENCES characters_subrace(id)
  DEFERRABLE INITIALLY DEFERRED;
"""

REVERSE_STAGE2 = r"""
ALTER TABLE characters_character
  DROP CONSTRAINT IF EXISTS characters_character_subrace_id_fkey;

ALTER TABLE characters_character RENAME COLUMN subrace_id    TO subrace_id_new;
ALTER TABLE characters_character RENAME COLUMN subrace_id_old TO subrace_id;
"""

class Migration(migrations.Migration):
    dependencies = [
        ("characters", "0044_characterclass_skill_points_per_level_and_more"),
    ]
    atomic = False  # critical: let the two stages commit separately
    operations = [
        migrations.RunSQL(SQL_STAGE1),
        migrations.RunSQL(SQL_STAGE2, REVERSE_STAGE2),
    ]
