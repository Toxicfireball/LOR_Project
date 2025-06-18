import os
import json
from django.core.management.base import BaseCommand
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from io import StringIO
from characters.models import Spell, ClassFeat
from django.db import connection

# ─── Constants ────────────────────────────────────────────────────────────────
LEVEL_MAP = {
    'Cantrips': 0,
    '1st Level': 1,  '2nd Level': 2,  '3rd Level': 3,
    '4th Level': 4,  '5th Level': 5,  '6th Level': 6,
    '7th Level': 7,  '8th Level': 8,  '9th Level': 9,
    '10th Level': 10,
}

# ─── Utility ──────────────────────────────────────────────────────────────────
def safe_str(value):
    """
    - If value is None or all-whitespace: return ''
    - If value is a string with any non-whitespace: return it unchanged
    - Otherwise, str(value)
    """
    if value is None:
        return ''
    if isinstance(value, str):
        # drop empty-or-all-whitespace cells
        return value if value.strip() else ''
    return str(value)

# ─── Command ──────────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = "Sync spells and feats from Google Sheets, preserving line-breaks."

    def handle(self, *args, **options):
        # DB info
        print("📡 DB ENGINE:", connection.settings_dict['ENGINE'], flush=True)
        print("📡 DB NAME:  ", connection.settings_dict['NAME'],  flush=True)
        print("🟢 SYNC JOB STARTED", flush=True)

        # Google creds
        json_creds = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
        if not json_creds:
            self.stderr.write("❌ ERROR: GOOGLE_SHEETS_CREDENTIALS_JSON not set")
            return

        creds_dict = json.loads(json_creds)
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        print("✅ Google Sheets client initialized", flush=True)

        try:
            # ─── SPELLS ─────────────────────────────────────────────────────
            spell_book = client.open_by_key(
                "1tUP5rXleImOKnrOVGBnmxNHHDAyU0HHxeuODgLDX8SM"
            )
            for sheet in spell_book.worksheets():
                title = sheet.title.strip()
                level = LEVEL_MAP.get(title, 0)
                print(f"📘 Processing sheet: {title}", flush=True)

                raw_rows = sheet.get_all_records()
                print(f"🔢 Found {len(raw_rows)} rows", flush=True)

                for raw in raw_rows:
                    # Strip only the keys; keep values intact
                    row = {k.strip(): v for k, v in raw.items()}
                    name_raw = row.get('Spell Name', '')
                    # Skip if name is blank or whitespace-only
                    if not (isinstance(name_raw, str) and name_raw.strip()):
                        print("⚠️ Skipping row with no Spell Name", flush=True)
                        continue

                    spell_name = name_raw.strip()  # still strip for lookup
                    Spell.objects.update_or_create(
                        name=spell_name,
                        defaults={
                            'level': level,
                            'classification': safe_str(row.get('Classification')),
                            'description':    safe_str(row.get('Description')),
                            'effect':         safe_str(row.get('Effect')),
                            'upcast_effect':  safe_str(row.get('Upcasted Effect')),
                            'saving_throw':   safe_str(row.get('Saving Throw')),
                            'casting_time':   safe_str(row.get('Casting Time')),
                            'duration':       safe_str(row.get('Duration')),
                            'components':     safe_str(row.get('Components')),
                            'range':          safe_str(row.get('Range')),
                            'target':         safe_str(row.get('Target')),
                            'school':         safe_str(row.get('School')),
                            'origin':         safe_str(row.get('Origin')),
                            'sub_origin':     safe_str(row.get('Sub Origin')),
                            'mastery_req':    safe_str(row.get('Mastery Req')),
                            'tags':           safe_str(row.get('Other Tags')),
                        }
                    )

            # ─── FEATS ──────────────────────────────────────────────────────
            feat_sheet = client.open_by_key(
                "1-WHN5KXt7O7kRmgyOZ0rXKLA6s6CbaOWFmvPflzD5bQ"
            ).sheet1
            raw_feats = feat_sheet.get_all_records()
            print(f"📗 Processing {len(raw_feats)} feats", flush=True)

            for raw in raw_feats:
                row = {k.strip(): v for k, v in raw.items()}
                name_raw = row.get('Feat', '')
                if not (isinstance(name_raw, str) and name_raw.strip()):
                    print("⚠️ Skipping row with no Feat name", flush=True)
                    continue

                feat_name = name_raw.strip()
                # Normalize Feat Type exactly as before
                raw_type = row.get('Feat Type', '')
                cleaned = raw_type.lower().replace('/', ',').replace('\\', ',')
                parts = [p.strip().capitalize() for p in cleaned.split(',') if p.strip()]
                parts = ['General' if p == 'Racial' else p for p in parts]
                parts = sorted(
                    set(parts),
                    key=lambda x: ['General', 'Class', 'Skill'].index(x)
                    if x in ['General', 'Class', 'Skill'] else x
                )
                normalized_feat_type = ", ".join(parts)

                ClassFeat.objects.update_or_create(
                    name=feat_name,
                    defaults={
                        'description':          safe_str(row.get('Description')),
                        'level_prerequisite':   safe_str(row.get('Level Prerequisite')),
                        'feat_type':            safe_str(normalized_feat_type),
                        'class_name':           safe_str(row.get('Class')),
                        'race':                 safe_str(row.get('Race')),
                        'tags':                 safe_str(row.get('Tags')),
                        'prerequisites':        safe_str(row.get('Pre-req')),
                    }
                )

            # ─── Summary ───────────────────────────────────────────────────
            total_spells = Spell.objects.count()
            total_feats  = ClassFeat.objects.count()
            print(f"📦 Total spells: {total_spells}", flush=True)
            print(f"📦 Total feats:  {total_feats}",  flush=True)
            print("✅ SYNC JOB DONE", flush=True)
            self.stdout.write(
                self.style.SUCCESS("Spells and Class Feats synced successfully.")
            )

        except Exception as e:
            print("❌ Exception occurred:", flush=True)
            import traceback
            traceback.print_exc()
            self.stderr.write(str(e))
