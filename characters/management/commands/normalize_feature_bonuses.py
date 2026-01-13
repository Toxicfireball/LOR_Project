# characters/management/commands/normalize_feature_bonuses.py

import re
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from characters.models import ClassFeature


# ──────────────────────────────────────────────────────────────────────────────
# MAPPINGS
# ──────────────────────────────────────────────────────────────────────────────
def _tierize_1_3_4_7_8_11(n: int) -> int:
    # Keep non-positive numbers unchanged (if you ever have them)
    if n <= 0:
        return n
    if n <= 3:
        return 1
    if n <= 7:
        return 2
    # 8+ clamps to 3 (you only defined tiers up to 11)
    return 3

def _map_armor_bonus(n: int) -> int | None:
    """
    ARMOR brackets (your rule):
      +1 Armor          -> removed
      +2..+4 Armor      -> +1 Armor
      +5..+9 Armor      -> +3 Armor
      else              -> keep as-is (extend if you want)
    Return None means "remove armor bonus entirely".
    """
    if n == 1:
        return None
    if 2 <= n <= 4:
        return 1
    if 5 <= n <= 9:
        return 3
    return n


def _map_armor_piercing_bonus(n: int) -> int:
    """
    ARMOR PIERCING brackets (your rule):
      +1..+3 Armor Piercing   -> +1
      +4..+7 Armor Piercing   -> +2
      +8..+11 Armor Piercing  -> +3
      else                    -> keep as-is (extend if you want)
    """
    if 1 <= n <= 3:
        return 1
    if 4 <= n <= 7:
        return 2
    if 8 <= n <= 11:
        return 3
    return n


# ──────────────────────────────────────────────────────────────────────────────
# TEXT REWRITES
# ──────────────────────────────────────────────────────────────────────────────


DODGE_RE = re.compile(r"\bdodge\b", flags=re.I)

def replace_dodge_with_defence(s: str) -> str:
    """
    Rename stat 'dodge' -> 'defence', but don't break verb phrases like:
      "dodge an attack" -> "defend against an attack"
    Also preserves casing for pure stat/name replacements.
    """
    if not s:
        return s

    out = s

    def _verb_against(verb: str):
        def _repl(m: re.Match) -> str:
            art = m.group(1) or ""
            noun = m.group(2)  # preserve original casing
            plural = noun.lower().endswith("s")
            # If plural, drop the article ("an attacks" is wrong)
            art_out = "" if plural else art
            return f"{verb} against {art_out}{noun}"
        return _repl

    # Handle verb uses first (so we don't turn them into the stat name)
    out = re.sub(
        r"\bdodge\s+((?:an?|the)\s+)?(attack|attacks|strike|strikes|hit|hits)\b",
        _verb_against("defend"),
        out,
        flags=re.I,
    )
    out = re.sub(
        r"\bdodging\s+((?:an?|the)\s+)?(attack|attacks|strike|strikes|hit|hits)\b",
        _verb_against("defending"),
        out,
        flags=re.I,
    )
    out = re.sub(
        r"\bdodged\s+((?:an?|the)\s+)?(attack|attacks|strike|strikes|hit|hits)\b",
        _verb_against("defended"),
        out,
        flags=re.I,
    )
    out = re.sub(
        r"\bdodges\s+((?:an?|the)\s+)?(attack|attacks|strike|strikes|hit|hits)\b",
        _verb_against("defends"),
        out,
        flags=re.I,
    )

    # Then stat/name replacement with casing preservation
    def repl(m: re.Match) -> str:
        w = m.group(0)
        if w.isupper():
            return "DEFENCE"
        if w[:1].isupper():
            return "Defence"
        return "defence"

    return DODGE_RE.sub(repl, out)

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _join_list(items: list[str]) -> str:
    """
    Match your style:
      1 item  -> "defence"
      2 items -> "defence, reflex"
      3+      -> "defence, reflex and armor"
    """
    items = [i.strip() for i in items if i and i.strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]}, {items[1]}"
    return ", ".join(items[:-1]) + " and " + items[-1]


def _parse_targets(raw: str) -> list[str]:
    """
    Parse a target list like:
      "defence, reflex and armor"
      "defence, reflex, and armor"
      "defence and armor"
    into ["defence", "reflex", "armor"].
    """
    s = (raw or "").strip()
    if not s:
        return []

    # normalize Oxford comma: ", and" -> " and"
    s = re.sub(r",\s*and\s+", " and ", s, flags=re.I)

    # split by commas, then split each chunk by "and"
    chunks = [c.strip() for c in s.split(",") if c.strip()]
    items: list[str] = []
    for c in chunks:
        parts = re.split(r"\s+and\s+", c, flags=re.I)
        items.extend([p.strip() for p in parts if p.strip()])

    return items


def _norm_token(x: str) -> str:
    """
    Normalize a token for comparison:
      - lowercase
      - treat hyphen as space
      - collapse whitespace
    So "Armor-Piercing" == "armor piercing".
    """
    x = (x or "").strip().lower().replace("-", " ")
    x = re.sub(r"\s+", " ", x)
    return x


# ──────────────────────────────────────────────────────────────────────────────
# REGEXES
# ──────────────────────────────────────────────────────────────────────────────

# Direct ARMOR:
# Matches "+2 Armor" or "+2 to armor"
# Avoids "Armor Class" by (?!\s*class\b)
DIRECT_ARMOR_RE = re.compile(
    r"(?P<lead>\s*)(?P<art>\b(?:a|an)\s+)?\+(?P<n>\d+)\s*(?P<to>to\s+)?(?P<armor>armor|armour)\b(?!\s*(?:class|piercing)\b)",
    flags=re.I,
)

# Direct ARMOR PIERCING:
# Matches "+2 Armor Piercing", "+2 to Armor-Piercing", etc.
DIRECT_AP_RE = re.compile(
    r"(?P<lead>\s*)\+(?P<n>\d+)\s*(?P<to>to\s+)?(?P<ap>(?:armor|armour)\s*(?:-| )\s*piercing)\b",
    flags=re.I,
)

# Shared lists:
# Matches "+2 to defence, reflex and armor" (or armor piercing)
# Stops at punctuation / HTML tag open "<" to reduce markup damage.
# Shared lists:
SHARED_LIST_RE = re.compile(
    r"\+(?P<n>\d+)\s+to\s+(?P<targets>[^<\n\r.;:+]*?\b(?:(?:armor|armour)\b(?!\s*class\b)|(?:armor|armour)\s*(?:-| )\s*piercing\b)[^<\n\r.;:+]*)",
    flags=re.I,
)

# "Bare" numeric armor mentions inside sentences, e.g. "and 2 armor", "by 4 armour"
BARE_ARMOR_RE = re.compile(
    r"(?P<lead>\b(?:and|or|,|by)\s+)(?P<n>\d+)\s+(?P<armor>armor|armour)\b(?!\s*(?:class|piercing)\b)",
    flags=re.I,
)

# "Bare" numeric armor piercing mentions inside sentences, e.g. "and 6 armor piercing"
BARE_AP_RE = re.compile(
    r"(?P<lead>\b(?:and|or|,|by)\s+)(?P<n>\d+)\s+(?P<ap>(?:armor|armour)\s*(?:-| )\s*piercing)\b",
    flags=re.I,
)



# ──────────────────────────────────────────────────────────────────────────────
# CORE NORMALIZER
# ──────────────────────────────────────────────────────────────────────────────

def normalize_description_text(html: str) -> str:
    """
    Applies:
      - dodge -> defence
      - Armor remap per brackets
      - Armor Piercing remap per brackets
    Handles:
      - direct tokens: "+N Armor", "+N to armor", "+N Armor Piercing"
      - shared lists: "+N to defence, reflex and armor"
    """
    if not html:
        return html

    out = replace_dodge_with_defence(html)

    # PASS A: direct "+N (to) armor"
    def repl_direct_armor(m: re.Match) -> str:
        n = int(m.group("n"))
        mapped = _map_armor_bonus(n)

        lead = m.group("lead") or ""
        art  = m.group("art") or ""   # "a " / "an " if present
        to   = m.group("to") or ""
        armor_word = m.group("armor")

        # +1 armor => remove it completely
        if mapped is None:
            return lead  # keep whitespace; cleanup pass collapses it

        if to:
            return f"{lead}{art}+{mapped} to {armor_word}"
        return f"{lead}{art}+{mapped} {armor_word}"

    out = DIRECT_ARMOR_RE.sub(repl_direct_armor, out)

    # PASS A2: direct "+N (to) armor piercing"
    def repl_direct_ap(m: re.Match) -> str:
        n = int(m.group("n"))
        mapped = _map_armor_piercing_bonus(n)

        to = m.group("to") or ""
        ap_word = m.group("ap")
        if to:
            return f"{m.group('lead')}+{mapped} to {ap_word}"
        return f"{m.group('lead')}+{mapped} {ap_word}"

    out = DIRECT_AP_RE.sub(repl_direct_ap, out)

    # PASS A3: bare "and/by N armor" (no plus / no "to")
    def repl_bare_armor(m: re.Match) -> str:
        n = int(m.group("n"))
        mapped = _map_armor_bonus(n)
        # IMPORTANT: if mapped is None (your "+1 armor removal" rule),
        # don't delete bare text like "by 1 armor" (it creates "by " garbage).
        if mapped is None:
            return m.group(0)
        return f"{m.group('lead')}{mapped} {m.group('armor')}"

    out = BARE_ARMOR_RE.sub(repl_bare_armor, out)

    # PASS A4: bare "and/by N armor piercing"
    def repl_bare_ap(m: re.Match) -> str:
        n = int(m.group("n"))
        mapped = _map_armor_piercing_bonus(n)
        return f"{m.group('lead')}{mapped} {m.group('ap')}"

    out = BARE_AP_RE.sub(repl_bare_ap, out)
    def repl_shared(m: re.Match) -> str:
        n = int(m.group("n"))
        targets_raw = m.group("targets") or ""
        low = targets_raw.lower()

        # If it contains another explicit +X inside the targets chunk, don't touch it.
        # e.g. "+1 to armor and +1 to saves"
        if re.search(r"\+\s*\d+", targets_raw):
            return m.group(0)

        # Only treat it as a "list" if it has commas or "and"
        if ("," not in targets_raw) and (" and " not in low):
            return m.group(0)

        items = _parse_targets(targets_raw)
        if not items:
            return m.group(0)

        armor_keys = {"armor", "armour"}
        ap_keys = {"armor piercing", "armour piercing"}

        armor_items = [i for i in items if _norm_token(i) in armor_keys]
        ap_items    = [i for i in items if _norm_token(i) in ap_keys]

        # If we didn't actually find armor/ap as standalone items, don't touch
        if not armor_items and not ap_items:
            return m.group(0)

        armor_word = armor_items[0] if armor_items else None  # preserve original spelling/case
        ap_word    = ap_items[0] if ap_items else None

        others = [
            i for i in items
            if _norm_token(i) not in armor_keys and _norm_token(i) not in ap_keys
        ]

        parts: list[str] = []

        # Keep "+n to <others>" as one clause
        if others:
            parts.append(f"+{n} to {_join_list(others)}")

        # Armor (may remove)
        if armor_word:
            mapped_armor = _map_armor_bonus(n)
            if mapped_armor is not None:
                parts.append(f"+{mapped_armor} to {armor_word}")
            # else omit armor entirely

        # Armor Piercing (remap once)
        if ap_word:
            mapped_ap = _map_armor_piercing_bonus(n)
            parts.append(f"+{mapped_ap} to {ap_word}")

        if not parts:
            return ""

        return " and ".join(parts)

    out = SHARED_LIST_RE.sub(repl_shared, out)

    # Cleanup whitespace/punctuation
    # Cleanup whitespace/punctuation
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    out = re.sub(r"\(\s+", "(", out)
    out = re.sub(r"\s+\)", ")", out)

    # NEW: remove lines that became incomplete after stripping "+1 to armor"
    # Examples:
    #   "While wearing armor you gain"  -> removed
    #   "You gain"                     -> removed (only if it’s the whole line)
    out = re.sub(
        r"(?im)^[ \t]*(?:while\s+wearing\s+(?:an?\s+)?(?:armor|armour)\s+)?(?:you\s+)?gain\s*$\r?\n?",
        "",
        out,
    )

    # OPTIONAL: if you have HTML-heavy descriptions, this helps remove empty tags created by deletions
    out = re.sub(r"(?i)<p[^>]*>\s*(?:&nbsp;)?\s*</p>", "", out)
    out = re.sub(r"(?i)<li[^>]*>\s*(?:&nbsp;)?\s*</li>", "", out)

    # Tighten up leftover blank lines
    out = re.sub(r"\n{3,}", "\n\n", out)

    return out.strip()



# ──────────────────────────────────────────────────────────────────────────────
# MANAGEMENT COMMAND
# ──────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        "Normalize ONLY ClassFeature.description (covers Race features via RacialFeature(ClassFeature)).\n"
        "Changes:\n"
        "  - dodge -> defence\n"
   "  - Armor brackets: +1-3 -> +1; +4-7 -> +2; +8-11 -> +3\n"
"  - Armor Piercing brackets: +1-3 -> +1; +4-7 -> +2; +8-11 -> +3\n"

    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write changes to DB (default is dry-run).")
        parser.add_argument("--limit", type=int, default=0, help="Limit rows processed (testing).")
        parser.add_argument("--show", type=int, default=25, help="Show up to N changed examples.")
        parser.add_argument("--ids", type=str, default="", help="Comma-separated feature IDs to process (optional).")

    def handle(self, *args, **opts):
        apply = bool(opts["apply"])
        limit = int(opts["limit"] or 0)
        show = int(opts["show"] or 25)
        ids_raw = (opts.get("ids") or "").strip()

        qs = ClassFeature.objects.all().only("id", "code", "name", "description").order_by("id")

        # Narrow to likely matches for speed (still safe)
        qs = qs.filter(
            Q(description__icontains="armor") |
            Q(description__icontains="armour") |
            Q(description__icontains="piercing") |
            Q(description__icontains="dodge")
        )

        if ids_raw:
            try:
                ids = [int(x.strip()) for x in ids_raw.split(",") if x.strip()]
                qs = qs.filter(id__in=ids)
            except Exception:
                self.stdout.write(self.style.ERROR("Bad --ids format. Use comma-separated integers."))
                return

        if limit > 0:
            qs = qs[:limit]

        changed = []
        shown = 0
        scanned = 0

        for f in qs.iterator():
            scanned += 1
            old = f.description or ""
            new = normalize_description_text(old)
            if new != old:
                f.description = new
                changed.append(f)

                if shown < show:
                    shown += 1
                    self.stdout.write(self.style.WARNING(f"\nID {f.id}  {f.code}  {f.name}"))
                    self.stdout.write("BEFORE:\n" + (old[:900] + ("..." if len(old) > 900 else "")))
                    self.stdout.write("AFTER:\n"  + (new[:900] + ("..." if len(new) > 900 else "")))

        self.stdout.write(f"\nScanned rows: {scanned}")
        self.stdout.write(f"Rows that would change: {len(changed)}")

        if not apply:
            self.stdout.write(self.style.NOTICE("Dry-run only. Re-run with --apply to write changes."))
            return

        with transaction.atomic():
            ClassFeature.objects.bulk_update(changed, ["description"], batch_size=500)

        self.stdout.write(self.style.SUCCESS(f"Updated {len(changed)} rows (description only)."))
