import os
import json
from django.core.management.base import BaseCommand
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from characters.models import Spell, ClassFeat
from django.db import connection, transaction
from django.db.models.deletion import ProtectedError   # ← ADD
from collections import defaultdict
def get_feat_name_from_row(row: dict) -> str:
    """
    Return the feat name exactly as in the sheet (trim edges only).
    Works even if the first column header (A1) is blank.
    """
    # include '' for a blank A1 header; gspread uses '' as the key
    candidates = ('Feat', 'Feat Name', 'Name', 'Feature', 'Class Feat', '', 'Unnamed: 0')
    for key in candidates:
        if key in row:
            v = row.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()

    # if any header contains "feat", use that
    for k, v in row.items():
        if 'feat' in str(k).lower() and isinstance(v, str) and v.strip():
            return v.strip()

    # final fallback: pick the first non-empty string value in row order
    for _, v in row.items():
        if isinstance(v, str) and v.strip():
            return v.strip()

    return ''


def first_nonempty(row: dict, *candidates: str) -> str:
    for k in candidates:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v
        if v not in (None, "") and not (isinstance(v, str) and not v.strip()):
            return str(v)
    return ""

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

class Command(BaseCommand):
    help = "Sync spells and feats from Google Sheets, preserving line-breaks."

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-missing',
            action='store_true',
            help='Delete ClassFeat rows not present in the sheet (case/space-insensitive).'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Log intended changes/deletions without modifying the database.'
        )
        parser.add_argument(
            '--min-sheet-rows',
            type=int,
            default=400,
            help='Safety: require at least this many feat rows from the sheet before allowing deletion.'
        )


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
                            'description':    safe_str(first_nonempty(row, 'Description', 'Desc')),
                            'effect':         safe_str(first_nonempty(row, 'Effect', 'Effects')),
                            'upcast_effect':  safe_str(first_nonempty(row, 'Upcasted Effect', 'Upcast Effect')),
                            'saving_throw':   safe_str(first_nonempty(row, 'Saving Throw', 'Save', 'Save (Type)')),
                            'casting_time':   safe_str(first_nonempty(row, 'Casting Time', 'Cast Time')),
                            'duration':       safe_str(first_nonempty(row, 'Duration', 'Dur')),
                            'components':     safe_str(first_nonempty(row, 'Components', 'Comp')),
                            'range':          safe_str(first_nonempty(row, 'Range')),
                            'target':         safe_str(first_nonempty(row, 'Target', 'Targets')),
                            'origin':         safe_str(first_nonempty(row, 'Origin', 'School', 'Tradition')),
                            'sub_origin':     safe_str(first_nonempty(row, 'Sub Origin', 'Sub-Origin')),
                            'mastery_req':    safe_str(first_nonempty(row, 'Mastery Req', 'Mastery Requirement')),
                            'tags':           safe_str(first_nonempty(row, 'Other Tags', 'Tags')),

                        }
                    )

            # ─── FEATS ──────────────────────────────────────────────────────
            feat_book = client.open_by_key("1-WHN5KXt7O7kRmgyOZ0rXKLA6s6CbaOWFmvPflzD5bQ")
            # Find the "Feats" tab robustly (trim spaces, case-insensitive)
            feat_sheet = None
            all_ws = feat_book.worksheets()
            for ws in all_ws:
                if ws.title.strip().lower() == "feats":
                    feat_sheet = ws
                    break

            if feat_sheet is None:
                titles = [ws.title for ws in all_ws]
                self.stderr.write(f"❌ Worksheet 'Feats' not found (even after trimming). Available tabs: {titles}")
                return

            # Optional transparency if the tab had stray whitespace/casing
            if feat_sheet.title != "Feats":
                print(f"⚠️ Using worksheet '{feat_sheet.title}' (normalized match for 'Feats').", flush=True)

            
            raw_feats = feat_sheet.get_all_records()
            if raw_feats:
                headers = [h.strip() for h in raw_feats[0].keys()]
                print(f"🧾 Sheet headers: {headers}", flush=True)
            else:
                print("⛔ ‘Feats’ tab returned 0 rows. Aborting feats sync to avoid accidental deletion.", flush=True)
                return

            # Safety: require a recognizable feat-name column AND at least one key metadata column
            header_norm = {h.lower() for h in headers}
            if not (any("feat" in h for h in header_norm) and ("description" in header_norm or "pre-req" in header_norm)):
                print(f"⛔ Header sanity check failed (got: {sorted(header_norm)}). Aborting feats sync.", flush=True)
                return

            verbosity = int(options.get('verbosity', 1))

            
            # Build a case/space-insensitive index of existing feats so we can update ALL duplicates
            existing_rows = list(ClassFeat.objects.all().values('id', 'name'))
            by_key = defaultdict(list)
            for r in existing_rows:
                key = canonical_name(r['name']).lower()
                if key:
                    by_key[key].append(r['id'])
            
            sheet_keys = set()              # keys present in the sheet (for deletion pass)
            display_by_key = dict()         # key -> exact display name from sheet (for dedupe keep-preference)
            
            pre_dup_groups = {k: v for k, v in by_key.items() if len(v) > 1}
            print(f"🧪 Pre-sync duplicate groups (case/space-insensitive): {len(pre_dup_groups)}", flush=True)
            if verbosity >= 2:
                for i, (k, ids) in enumerate(list(pre_dup_groups.items())[:5], start=1):
                    print(f"   {i:02d}. key='{k}' ids={ids}", flush=True)
            
            created, updated = 0, 0
            sample_debug = []
            
            with transaction.atomic():
                for idx, raw in enumerate(raw_feats, start=1):
                    # Strip headers; keep values exactly.
                    row = {k.strip(): v for k, v in raw.items()}
            
                    # Feat name: store EXACTLY as the sheet has it (trim edges only).
                    feat_name = get_feat_name_from_row(row)
                    if not feat_name:
                        if verbosity >= 1 and idx <= 5:
                            print(f"⚠️ Skipping row with no resolvable feat name; headers={list(row.keys())}", flush=True)
                        continue
            
                    key = canonical_name(feat_name).lower()
                    sheet_keys.add(key)
                    # Remember the exact display name the sheet uses for this key
                    display_by_key[key] = feat_name
            
                    # Store column values AS-IS from the sheet (no normalization/re-ordering)
                    feat_type_cell = row.get('Feat Type')
                    fields = dict(
                        description        = safe_str(row.get('Description')),
                        level_prerequisite = safe_str(row.get('Level Prerequisite')),
                        feat_type          = '' if feat_type_cell is None else str(feat_type_cell),
                        class_name         = safe_str(row.get('Class')),
                        race               = safe_str(row.get('Race')),
                        tags               = safe_str(row.get('Tags')),
                        # Use the exact canonical header used in the sheet for prerequisites:
                        prerequisites      = safe_str(row.get('Pre-req')),
                    )
            
                    ids = by_key.get(key, [])
            
                    if not ids:
                        # Create new row (exact sheet values)
                        obj = ClassFeat.objects.create(name=feat_name, **fields)
                        by_key[key] = [obj.id]
                        created += 1
                        if len(sample_debug) < 5:
                            sample_debug.append((feat_name, 'created', obj.id, fields['feat_type']))
                    else:
                        # Update ALL duplicates so any that your UI references get refreshed identically
                        for fid in ids:
                            ClassFeat.objects.filter(id=fid).update(name=feat_name, **fields)
                            updated += 1
                        if verbosity >= 2 and len(ids) > 1:
                            print(f"🔁 De-dup group for '{feat_name}': updated {len(ids)} rows (ids={ids})", flush=True)
            
            print(f"📦 Feats → created: {created}, updated rows: {updated}", flush=True)

            
            # Post-sync duplicate report + HARD de-dupe (to mirror sheet 1:1)
            existing_rows = list(ClassFeat.objects.all().values('id', 'name'))
            post_by_key = defaultdict(list)
            for r in existing_rows:
                k = canonical_name(r['name']).lower()
                if k:
                    post_by_key[k].append(r['id'])
            
            dup_groups = {k: v for k, v in post_by_key.items() if len(v) > 1}
            print(f"🧪 Post-sync duplicate groups (case/space-insensitive): {len(dup_groups)}", flush=True)
            
            # HARD DE-DUPE: keep exactly one row per key (prefer exact sheet display name match)
            deleted_dups = kept = protected_dups = 0
            for key, ids in dup_groups.items():
                rows = list(ClassFeat.objects.filter(id__in=ids).values('id', 'name'))
            
                # Prefer the row whose name exactly equals the sheet display name for this key
                preferred_name = display_by_key.get(key)
                keep_id = None
                if preferred_name is not None:
                    for r in rows:
                        if r['name'] == preferred_name:
                            keep_id = r['id']
                            break
            
                # Fallback: keep the lowest id
                if keep_id is None:
                    keep_id = min(ids)
            
                delete_ids = [i for i in ids if i != keep_id]
                kept += 1
            
                for fid in delete_ids:
                    try:
                        ClassFeat.objects.filter(id=fid).delete()
                        deleted_dups += 1
                    except ProtectedError:
                        protected_dups += 1
                        # If protected, we can't delete; leave it as is.
            
            if dup_groups:
                print(f"🧹 De-dupe: kept {kept}, deleted {deleted_dups}, protected (kept) {protected_dups}.", flush=True)
            else:
                print("👍 No duplicates after sync.", flush=True)

            
            # Optional: clear cache if you render feats from cached views
            if os.environ.get('SYNC_CLEAR_CACHE') == '1':
                try:
                    from django.core.cache import cache
                    cache.clear()
                    print("🧹 Cache cleared (SYNC_CLEAR_CACHE=1).", flush=True)
                except Exception as _:
                    pass
            
            # ── Deletion pass: remove feats NOT present in the sheet (case/space-insensitive) ──
            # ── Deletion pass (SAFE): remove feats NOT present in the sheet only with strong guardrails ──
            del_missing = bool(options.get('delete_missing'))
            dry_run     = bool(options.get('dry_run'))
            min_rows    = int(options.get('min_sheet_rows', 400))

            if not del_missing:
                print("ℹ️  Skipping deletion of missing feats (use --delete-missing to enable).", flush=True)
            else:
                print("🧮 Building deletion set (feats missing from sheet)...", flush=True)
                total_db = ClassFeat.objects.count()
                print(f"   • sheet_keys gathered: {len(sheet_keys)}", flush=True)
                print(f"   • current DB feats:    {total_db}", flush=True)

                # Safety rails (1): Basic row count sanity
                if len(sheet_keys) == 0:
                    print("⛔ Abort: sheet yielded 0 feat rows (wrong tab/header/permissions?). No deletions performed.", flush=True)
                elif len(sheet_keys) < min_rows:
                    print(f"⛔ Abort: only {len(sheet_keys)} feat rows < min-sheet-rows={min_rows}. Raise --min-sheet-rows if intentional.", flush=True)
                else:
                    # Safety rails (2): Overlap sanity check vs DB (require ≥80% overlap)
                    all_db_rows = list(ClassFeat.objects.all().values('id', 'name'))
                    db_keys = [canonical_name(r['name']).lower() for r in all_db_rows if r['name']]
                    db_total = len(db_keys)
                    overlap = sum(1 for k in db_keys if k in sheet_keys)
                    overlap_ratio = (overlap / db_total) if db_total else 1.0
                    print(f"   • overlap with DB: {overlap}/{db_total} ({overlap_ratio:.1%})", flush=True)

                    if overlap_ratio < 0.80:
                        print("⛔ Abort: overlap < 80%. Refusing to delete (sheet likely misread or headers wrong).", flush=True)
                    else:
                        # Safety rails (3): Explicit operator confirmation via env
                        confirm_env = os.environ.get("SYNC_CONFIRM_DELETE", "").lower() == "yes"
                        if not confirm_env:
                            print("⛔ Abort: set SYNC_CONFIRM_DELETE=YES to allow deletions.", flush=True)
                        else:
                            # Safety rails (4): Require some create/update activity in this run
                            if (created + updated) == 0:
                                print("⛔ Abort: 0 rows created/updated in this run; refusing to delete.", flush=True)
                            else:
                                # Compute deletion set
                                to_delete = []
                                for r in all_db_rows:
                                    k = canonical_name(r['name']).lower()
                                    if k and k not in sheet_keys:
                                        to_delete.append((r['id'], r['name']))

                                print(f"🗑️  Feats to delete: {len(to_delete)}", flush=True)
                                if to_delete:
                                    if dry_run:
                                        print(f"🧪 DRY RUN: would delete ids={[fid for fid, _ in to_delete[:50]]}{' ...' if len(to_delete) > 50 else ''}", flush=True)
                                    else:
                                        deleted_ok = protected = 0
                                        for fid, fname in to_delete:
                                            try:
                                                ClassFeat.objects.filter(id=fid).delete()
                                                deleted_ok += 1
                                                if verbosity >= 2 and deleted_ok <= 10:
                                                    print(f"   ✔ Deleted id={fid} name='{fname}'", flush=True)
                                            except ProtectedError:
                                                protected += 1
                                                print(f"   ⛔ Protected (kept) id={fid} name='{fname}'", flush=True)
                                        print(f"✅ Deletion done. Removed {deleted_ok}; kept (protected) {protected}.", flush=True)
                                else:
                                    print("👍 No feats to delete; DB matches sheet (by canonical name).", flush=True)

            
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
