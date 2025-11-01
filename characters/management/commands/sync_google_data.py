import os
import json
from django.core.management.base import BaseCommand
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from io import StringIO
from characters.models import Spell, ClassFeat
from django.db import connection, transaction   # CHANGED
from collections import defaultdict
def canonical_name(s: str) -> str:
    """
    Normalize for matching & de-duping:
    - collapse internal whitespace runs to single space
    - strip edges
    - preserve original casing for storage; we lower() only for keys
    """
    if s is None:
        return ''
    return " ".join(str(s).split()).strip()

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
                            'origin':         safe_str(row.get('Origin')),
                            'sub_origin':     safe_str(row.get('Sub Origin')),
                            'mastery_req':    safe_str(row.get('Mastery Req')),
                            'tags':           safe_str(row.get('Other Tags')),
                        }
                    )

            # ─── FEATS ──────────────────────────────────────────────────────
            feat_sheet = client.open_by_key("1-WHN5KXt7O7kRmgyOZ0rXKLA6s6CbaOWFmvPflzD5bQ").sheet1
            raw_feats = feat_sheet.get_all_records()
            print(f"📗 Processing {len(raw_feats)} feats", flush=True)
            
            verbosity = int(options.get('verbosity', 1))
            
            # Build a case/space-insensitive index of existing feats so we can update ALL duplicates
            existing_rows = list(ClassFeat.objects.all().values('id', 'name'))
            by_key = defaultdict(list)
            for r in existing_rows:
                key = canonical_name(r['name']).lower()
                if key:
                    by_key[key].append(r['id'])
            
            pre_dup_groups = {k: v for k, v in by_key.items() if len(v) > 1}
            print(f"🧪 Pre-sync duplicate groups (case/space-insensitive): {len(pre_dup_groups)}", flush=True)
            if verbosity >= 2:
                for i, (k, ids) in enumerate(list(pre_dup_groups.items())[:5], start=1):
                    print(f"   {i:02d}. key='{k}' ids={ids}", flush=True)
            
            created, updated = 0, 0
            sample_debug = []
            
            with transaction.atomic():
                for idx, raw in enumerate(raw_feats, start=1):
                    row = {k.strip(): v for k, v in raw.items()}
                    name_raw = row.get('Feat', '')
            
                    if not (isinstance(name_raw, str) and name_raw.strip()):
                        if verbosity >= 2:
                            print("⚠️ Skipping row with no Feat name", flush=True)
                        continue
            
                    # Canonicalize for both matching and storage
                    feat_name = canonical_name(name_raw)
                    key = feat_name.lower()
            
                    # Normalize feat_type (LOG when 'Racial' is remapped)
                    raw_type = row.get('Feat Type', '')
                    cleaned = raw_type.lower().replace('/', ',').replace('\\', ',')
                    parts = [p.strip().capitalize() for p in cleaned.split(',') if p.strip()]
                    if 'racial' in cleaned and verbosity >= 1:
                        print(f"ℹ️  '{feat_name}': mapping 'Racial' → 'General' (verify UI filters)", flush=True)
                    parts = sorted(
                        set(parts),
                        key=lambda x: ['General', 'Class', 'Skill'].index(x)
                            if x in ['General', 'Class', 'Skill'] else x
                    )
                    normalized_feat_type = ", ".join(parts)
            
                    fields = dict(
                        description        = safe_str(row.get('Description')),
                        level_prerequisite = safe_str(row.get('Level Prerequisite')),
                        feat_type          = safe_str(normalized_feat_type),
                        class_name         = safe_str(row.get('Class')),
                        race               = safe_str(row.get('Race')),
                        tags               = safe_str(row.get('Tags')),
                        prerequisites      = safe_str(row.get('Pre-req')),
                    )
            
                    ids = by_key.get(key, [])
            
                    if not ids:
                        # No existing rows (by case/space-insensitive key): create new
                        obj = ClassFeat.objects.create(name=feat_name, **fields)
                        by_key[key] = [obj.id]
                        created += 1
                        if len(sample_debug) < 5:
                            sample_debug.append((feat_name, 'created', obj.id, fields['feat_type']))
                    else:
                        # Update ALL duplicates so the one your UI uses is guaranteed to refresh
                        for fid in ids:
                            ClassFeat.objects.filter(id=fid).update(name=feat_name, **fields)
                            updated += 1
                        if verbosity >= 2 and len(ids) > 1:
                            print(f"🔁 De-dup group for '{feat_name}': updated {len(ids)} rows (ids={ids})", flush=True)
            
            print(f"📦 Feats → created: {created}, updated rows: {updated}", flush=True)
            
            # Post-sync duplicate report
            existing_rows = list(ClassFeat.objects.all().values('id', 'name'))
            post_by_key = defaultdict(list)
            for r in existing_rows:
                k = canonical_name(r['name']).lower()
                if k:
                    post_by_key[k].append(r['id'])
            dup_groups = {k: v for k, v in post_by_key.items() if len(v) > 1}
            print(f"🧪 Post-sync duplicate groups (case/space-insensitive): {len(dup_groups)}", flush=True)
            if verbosity >= 2:
                for i, (k, ids) in enumerate(list(dup_groups.items())[:5], start=1):
                    print(f"   {i:02d}. key='{k}' ids={ids}", flush=True)
            
            # Sample verification lines
            for name, action, pk, ftype in sample_debug:
                print(f"🔎 Sample: '{name}' [{action} id={pk}] feat_type='{ftype}'", flush=True)
            
            # Optional: clear cache if you render feats from cached views
            if os.environ.get('SYNC_CLEAR_CACHE') == '1':
                try:
                    from django.core.cache import cache
                    cache.clear()
                    print("🧹 Cache cleared (SYNC_CLEAR_CACHE=1).", flush=True)
                except Exception as _:
                    pass


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
