from django.shortcuts import render
from django.contrib import messages

from django.db.models import Case, When, IntegerField
# Create your views here.
# characters/views.py
from collections import defaultdict
from collections import Counter
from campaigns.models import CampaignMembership
from django.db.models import Q, Max
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django_select2.views import AutoResponseView
from .models import Character, Skill  , RaceFeatureOption  
from campaigns.models import Campaign
from django.db import models
import math
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
FIVE_TIERS = ["Untrained", "Trained", "Expert", "Master", "Legendary"]
# ---- Background helpers ------------------------------------------------------
from .models import Spell, CharacterKnownSpell, CharacterPreparedSpell, CharacterSkillPointTx
from django.db.models import Q
from django.views.decorators.http import require_GET
# ── helpers that read the LEVEL TRIGGER instead of JSON ───────────────────
import uuid

# put near the top of views.py (import re if not already)
import re, math

def _normalize_formula(expr: str) -> str:
    """Make data-entry formulas Python-evaluable."""
    if not expr:
        return ""
    s = str(expr)

    # Fix common English function names/phrases
    s = re.sub(r'(?i)\bround\s*up\s*\(', 'ceil(', s)      # "round up(" → ceil(
    s = re.sub(r'(?i)\broundup\s*\(',   'ceil(', s)       # "roundup(" → ceil(
    s = re.sub(r'(?i)\bceiling\s*\(',   'ceil(', s)       # "ceiling(" → ceil(

    # Be permissive with whitespace and case
    s = s.strip().lower()
    return s

def _picks_for_trigger(trigger, base_cls, cls_level):
    """
    'Choices granted at this level' → how many modules the player picks now.
    Prefers the pivot (ClassLevelFeature.choices_granted), falls back to
    trigger.choices_granted on the feature.
    """
    from .models import ClassLevel
    try:
        cl = ClassLevel.objects.get(character_class=base_cls, level=cls_level)
    except ClassLevel.DoesNotExist:
        return int(getattr(trigger, "choices_granted", 1) or 1)

    # Try the through model if it exists
    try:
        from .models import ClassLevelFeature  # your M2M through that stores choices_granted
        clf = ClassLevelFeature.objects.filter(class_level=cl, feature=trigger).first()
        if clf and getattr(clf, "choices_granted", None) not in (None, ""):
            return int(clf.choices_granted)
    except Exception:
        pass

    # Fallback to the feature field itself
    return int(getattr(trigger, "choices_granted", 1) or 1)


def _allowed_rank_from_trigger(trigger):
    """
    'Mastery Rank' on the gain_subclass_feat feature → max rank the player may
    select up to *this level*. If blank/NULL, treat as unlimited.
    """
    mr = getattr(trigger, "mastery_rank", None)
    return (int(mr) if mr not in (None, "") else None)


def _racefeat_details_kv(f):
    """
    RaceFeature → compact (label, value) list, hiding Scope/Kind/Activity-ish fields.
    """
    try:
        kv = _feature_details_map(f)
    except Exception:
        kv = []
        for k, label in [
            ("code", "Code"),
            ("name", "Name"),
            ("description", "Description"),
            ("uses", "Uses"),
            ("formula", "Formula"),
            ("formula_target", "Formula Target"),
            ("saving_throw_type", "Save Type"),
            ("saving_throw_granularity", "Save Granularity"),
        ]:
            v = getattr(f, k, None)
            if v not in (None, "", [], {}):
                kv.append((label, v))
    # normalize to list-of-dicts
    if isinstance(kv, dict):
        kv = list(kv.items())
    return [{"label": k, "value": v} for k, v in kv if v not in (None, "", [], {})]
def _modules_required(grp) -> int:
    try:
        return max(1, int(getattr(grp, "modules_required", 2) or 2))
    except Exception:
        return 2

def _current_mastery_tier(character, subclass, grp) -> int:
    """Zero-based tier. Advances after every N modules (group.modules_required)."""
    taken = (CharacterFeature.objects
             .filter(character=character,
                     subclass=subclass,
                     feature__scope='subclass_feat')
             .count())
    return taken // _modules_required(grp)

def _trigger_mastery_cap(trigger):
    """Mastery cap taken directly from the *gain subclass feature* (gainer)."""
    r = getattr(trigger, "mastery_rank", None)
    return (int(r) if r is not None else None)



# views.py
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
# characters/views.py
from urllib.parse import urlencode
from django.shortcuts import render
from django.urls import reverse
from django.db.models import Q

from .models import (
    # “code” &/or “name”
    CharacterClass, ClassSubclass, SubclassGroup, ClassFeature,
    Race, Subrace, Background, Language, ResourceType, WearableSlot,
    Skill, SubSkill, Weapon, Armor, WeaponTrait, ArmorTrait,
    Spell, ClassFeat, MartialMastery,
    Rulebook, RulebookPage, LoremasterArticle,ClassSkillFeatGrant
)

def _display_text(obj):
    # Prefer human-friendly main field
    for attr in ("name", "title"):
        if hasattr(obj, attr) and getattr(obj, attr):
            return getattr(obj, attr)
    return str(obj)

def _code_text(obj):
    # Collect a sensible “code-like” field if present
    for attr in ("code", "class_ID", "slug"):
        if hasattr(obj, attr) and getattr(obj, attr):
            return getattr(obj, attr)
    return ""

def _detail_url(obj):
    # Link where we know we have detail pages;
    # otherwise send users to a Codex list with a pre-filled query (?q=...)
    try:
        if isinstance(obj, CharacterClass):
            return reverse("characters:class_detail", kwargs={"pk": obj.pk})
        if isinstance(obj, Race):
            return reverse("characters:race_detail", kwargs={"pk": obj.pk})
        if isinstance(obj, Rulebook):
            return reverse("characters:rulebook_detail", kwargs={"pk": obj.pk})
        if isinstance(obj, RulebookPage):
            return reverse("characters:rulebook_page_detail",
                           kwargs={"rulebook_pk": obj.rulebook_id, "pk": obj.pk})
        if isinstance(obj, LoremasterArticle):
            return obj.get_absolute_url()  # already defined in your model

        # Codex list pages – we pass a ?q=... so users land filtered
        name_qs = urlencode({"q": _display_text(obj)})
        if isinstance(obj, Weapon):
            return reverse("characters:codex_weapons") + f"?{name_qs}"
        if isinstance(obj, Armor):
            return reverse("characters:codex_armor") + f"?{name_qs}"
        if isinstance(obj, Spell):
            return reverse("characters:codex_spells") + f"?{name_qs}"
        if isinstance(obj, ClassFeat):
            return reverse("characters:codex_feats") + f"?{name_qs}"

        # Fallback: None (still listed, just no link)
        return None
    except Exception:
        return None

def _search_model(model, code_fields, name_fields, query, limit_each=30):
    """
    Rank order within a model:
      1) exact code   (rank 0)
      2) startswith   (rank 1)
      3) icontains    (rank 2)
    Dedup across the three passes.
    """
    seen = set()
    items = []

    def push(obj, rank):
        key = (obj.__class__.__name__, obj.pk)
        if key in seen: 
            return
        seen.add(key)
        items.append({
            "pk": obj.pk,
            "display": _display_text(obj),
            "code": _code_text(obj),
            "url": _detail_url(obj),
            "rank": rank,
        })

    # 1) exact code
    if code_fields:
        q = Q()
        for f in code_fields:
            q |= Q(**{f + "__iexact": query})
        for obj in model.objects.filter(q)[:limit_each]:
            push(obj, 0)

    # 2) startswith (code + name)
    if name_fields or code_fields:
        q = Q()
        for f in code_fields + name_fields:
            q |= Q(**{f + "__istartswith": query})
        for obj in model.objects.filter(q)[:limit_each]:
            push(obj, 1)

    # 3) contains (code + name)
    if name_fields or code_fields:
        q = Q()
        for f in code_fields + name_fields:
            q |= Q(**{f + "__icontains": query})
        for obj in model.objects.filter(q)[:limit_each]:
            push(obj, 2)

    # Stable sort by rank then display text
    items.sort(key=lambda x: (x["rank"], x["display"].lower()))
    return items

def global_search(request):
    query = (request.GET.get("q") or "").strip()

    # What we search (easy to extend)
    SEARCHABLES = [
        # label, model, code_fields, name_fields
        ("Features",            ClassFeature,    ["code"],        ["name"]),
        ("Classes",             CharacterClass,  ["class_ID"],    ["name"]),
        ("Subclass Groups",     SubclassGroup,   ["code"],        ["name"]),
        ("Subclasses",          ClassSubclass,   ["code"],        ["name"]),
        ("Races",               Race,            ["code"],        ["name"]),
        ("Subraces",            Subrace,         ["code"],        ["name"]),
        ("Backgrounds",         Background,      ["code"],        ["name"]),
        ("Languages",           Language,        ["code"],        ["name"]),
        ("Resource Types",      ResourceType,    ["code"],        ["name"]),
        ("Wearable Slots",      WearableSlot,    ["code"],        ["name"]),
        ("Skills",              Skill,           [],              ["name"]),
        ("Sub-skills",          SubSkill,        [],              ["name"]),
        ("Weapons",             Weapon,          [],              ["name"]),
        ("Armor",               Armor,           [],              ["name"]),
        ("Weapon Traits",       WeaponTrait,     [],              ["name"]),
        ("Armor Traits",        ArmorTrait,      [],              ["name"]),
        ("Spells",              Spell,           [],              ["name"]),
        ("Feats",               ClassFeat,       [],              ["name"]),
        ("Martial Masteries",   MartialMastery,  [],              ["name"]),
        ("Rulebooks",           Rulebook,        [],              ["name"]),
        ("Rulebook Pages",      RulebookPage,    [],              ["title"]),
        ("Loremaster Articles", LoremasterArticle, ["slug"],      ["title"]),
    ]

    results = []
    total_count = 0

    if query:
        for label, model, code_fields, name_fields in SEARCHABLES:
            model_items = _search_model(model, code_fields, name_fields, query)
            if model_items:
                results.append({
                    "label": label,
                    "items": model_items,
                })
                total_count += len(model_items)

    # Pull exact-code hits (rank 0) to a top “Exact code matches” section
    top_exact = []
    for group in results:
        exacts = [it for it in group["items"] if it["rank"] == 0]
        if exacts:
            top_exact.extend([dict(it, section=group["label"]) for it in exacts])

    context = {
        "q": query,
        "top_exact": top_exact,     # flattened, rank==0
        "groups": results,          # grouped sections (rank-mixed)
        "total_count": total_count,
    }
    return render(request, "global_search.html", context)


from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from .models import (
    MartialMastery, CharacterClass, Weapon, WeaponTrait
)

# ---- Codex: Martial Masteries (list) ----------------------------------------
def mastery_list(request):
    # Preload filter sources
    classes = CharacterClass.objects.order_by("name").values("id", "name")
    traits  = WeaponTrait.objects.order_by("name").values("id", "name")
    # Weapon.DAMAGE_CHOICES = [('bludgeoning','Bludgeoning'), ...]
    damage_choices = [{"code": c[0], "label": c[1]} for c in Weapon.DAMAGE_CHOICES]
    range_choices  = [{"code": Weapon.MELEE, "label": "Melee"},
                      {"code": Weapon.RANGED, "label": "Ranged"}]
    # Action choices (kept local to avoid import gymnastics)
    action_choices = [
        ("action_1","One Action"), ("action_2","Two Actions"),
        ("action_3","Three Actions"), ("reaction","Reaction"), ("free","Free Action"),
    ]
    return render(request, "codex/codex_masteries.html", {
        "classes": list(classes),
        "traits":  list(traits),
        "damage_choices": damage_choices,
        "range_choices":  range_choices,
        "action_choices": action_choices,
    })


# ---- Data endpoint for dynamic filtering ------------------------------------
def mastery_data(request):
    qs = (MartialMastery.objects
          .prefetch_related(
              "classes",
              "allowed_weapons",
              "allowed_traits",
          )
          .order_by("level_required", "name"))

    # Text search
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

    # Class filter (multi)
    class_ids = request.GET.getlist("class")
    if class_ids:
        qs = qs.filter(Q(all_classes=True) | Q(classes__id__in=class_ids)).distinct()

    # Range filter (multi)
    ranges = request.GET.getlist("range")
    if ranges:
        qs = qs.filter(
            Q(restrict_to_range=False) |
            Q(allowed_range_types__overlap=ranges)
        )

    # Trait filter (multi)
    trait_ids = [int(t) for t in request.GET.getlist("trait") if t.isdigit()]
    if trait_ids:
        qs = qs.filter(
            Q(restrict_to_traits=False) |
            Q(allowed_traits__id__in=trait_ids)
        ).distinct()

    # Damage-type filter (multi)
    dmgs = request.GET.getlist("damage")
    if dmgs:
        qs = qs.filter(
            Q(restrict_to_damage=False) |
            Q(allowed_damage_types__overlap=dmgs)
        )

    # Action filter (single)
    actions = request.GET.getlist("action")
    if actions:
        qs = qs.filter(action_cost__in=actions)


    # Rare
    if (request.GET.get("rare") or "").lower() in ("1","true","yes","on"):
        qs = qs.filter(is_rare=True)

    # Ability gate present?
    if (request.GET.get("ability_gated") or "").lower() in ("1","true","yes","on"):
        qs = qs.filter(restrict_by_ability=True)

    # Numeric ranges
    def as_int(v, default=None):
        try: return int(v)
        except: return default

    lvl_min = as_int(request.GET.get("level_min"))
    lvl_max = as_int(request.GET.get("level_max"))
    if lvl_min is not None: qs = qs.filter(level_required__gte=lvl_min)
    if lvl_max is not None: qs = qs.filter(level_required__lte=lvl_max)

    cost_max = as_int(request.GET.get("cost_max"))
    if cost_max is not None:
        qs = qs.filter(points_cost__lte=cost_max)

    # Serialize
    data = []
    for m in qs:
        restrict_bits = []
        if m.restrict_to_range:
            restrict_bits.append(f"Range: {', '.join(m.allowed_range_types or [])}")
        if m.restrict_to_weapons:
            names = list(m.allowed_weapons.values_list("name", flat=True)[:6])
            extra = m.allowed_weapons.count() - len(names)
            restrict_bits.append("Weapons: " + ", ".join(names) + (f" (+{extra} more)" if extra>0 else ""))
        if m.restrict_to_traits:
            names = list(m.allowed_traits.values_list("name", flat=True)[:6])
            extra = m.allowed_traits.count() - len(names)
            mode  = "ALL" if (m.trait_match_mode or "").lower()=="all" else "ANY"
            restrict_bits.append(f"Traits ({mode}): " + ", ".join(names) + (f" (+{extra} more)" if extra>0 else ""))
        if getattr(m, "restrict_to_damage", False):
            restrict_bits.append("Damage: " + ", ".join(m.allowed_damage_types or []))

        data.append({
            "id": m.id,
            "name": m.name,
            "level": m.level_required,
            "cost": m.points_cost,
            "action": m.get_action_cost_display() if m.action_cost else "—",
            "rare": m.is_rare,
            "ability_req": {
                "on": m.restrict_by_ability,
                "ability": m.get_required_ability_display() if m.required_ability else None,
                "score": m.required_ability_score,
            },
            "classes": list(m.classes.values_list("name", flat=True)),
            "restrictions": restrict_bits,
            "url":  request.build_absolute_uri(
                        reverse("characters:mastery_detail", args=[m.pk])
                    ),
        })
    return JsonResponse({"results": data})


# ---- Detail page -------------------------------------------------------------
def mastery_detail(request, pk):
    m = get_object_or_404(
        MartialMastery.objects
            .prefetch_related("classes", "allowed_weapons", "allowed_traits"),
        pk=pk
    )
    return render(request, "codex/mastery_detail.html", {"m": m})


@require_GET
@login_required
def race_features_data(request):
    race_id    = request.GET.get("race")
    subrace_id = request.GET.get("subrace")

    try:
        race = Race.objects.get(pk=int(race_id))
    except Exception:
        return HttpResponseBadRequest("Invalid race")

    feats_qs = (
        race.features
            .select_related("character_class", "subrace", "subclass_group")
            .prefetch_related(
                "subclasses",
                "gain_subskills",
                "race_options__grants_feature__subclass_group__subclasses",  # ⬅ subclasses for nested subclass_choice
                "spell_slot_rows"
            )
            .order_by("name")
    )

    # ① hide all features that are *targets* of race options (only appear within the option)
    granted_ids = set(
        RaceFeatureOption.objects
            .filter(feature__race=race)
            .values_list("grants_feature_id", flat=True)
    )

    # ② buckets
    universal = [f for f in feats_qs if not f.subrace_id and not f.character_class_id and f.id not in granted_ids]

    class_map = {}
    for f in feats_qs:
        if f.character_class_id and not f.subrace_id and f.id not in granted_ids:
            key = getattr(f.character_class, "name", "—")
            class_map.setdefault(key, []).append(f)

    sid = None
    try:
        sid = int(subrace_id) if subrace_id else None
    except Exception:
        sid = None
    subrace_feats = [f for f in feats_qs if sid and f.subrace_id == sid and f.id not in granted_ids]

    def ser(f):
        # ----- options, robust -----
        ros = []
        opts_mgr = getattr(f, "race_options", None)
        if opts_mgr:
            for opt in opts_mgr.all():
                row = {"id": opt.id, "label": opt.label}
                gf = opt.grants_feature
                if gf:
                    gf_group = getattr(gf, "subclass_group", None)
                    gf_is_sc = ((getattr(gf, "scope", "") or "").strip().lower() == "subclass_choice")
                    subclasses = []
                    if gf_group:
                        for s in gf_group.subclasses.all():
                            subclasses.append({"id": s.id, "name": s.name})
                    row["grants_feature"] = {
                        "id": gf.id,
                        "name": gf.name or gf.code or "Feature",
                        "is_subclass_choice": gf_is_sc,                # ⬅ nested subclass picker flag
                        "subclass_group": gf_group.name if gf_group else None,
                        "subclasses": subclasses,                      # ⬅ subclasses for the nested picker
                        "details": _racefeat_details_kv(gf),
                        "description_html": getattr(gf, "description", "") or "",
                    }
                ros.append(row)

        # ----- top-level subclass choice (unchanged; we’re still *hiding* Scope/Kind/Activity in details) -----
        group = getattr(f, "subclass_group", None)
        subclasses = [{"id": s.id, "name": s.name} for s in (group.subclasses.all() if group else [])]
        is_sc = bool(subclasses) and ((getattr(f, "scope", "") or "").strip().lower() == "subclass_choice")

        return {
            "id": f.id,
            "name": f.name or f.code or "Feature",
            "subclass_group": group.name if group else None,
            "subclasses": subclasses,
            "is_subclass_choice": is_sc,

            # choice UX
            "has_race_options": len(ros) > 0,
            "needs_choice": bool(subclasses) or len(ros) > 0,
            "race_options": ros,                     # ⬅ only used for asking choices

            # details/desc (already hide Scope/Kind/Activity)
            "details": _racefeat_details_kv(f),
            "description_html": getattr(f, "description", "") or "",
        }

    payload = {
        "universal_features": [ser(f) for f in universal],
        "class_features_by_class": [
            {"class_name": cname, "features": [ser(f) for f in sorted(fs, key=lambda x: (x.name or ""))]}
            for cname, fs in sorted(class_map.items(), key=lambda kv: kv[0])
        ],
        "subrace_features": [ser(f) for f in sorted(subrace_feats, key=lambda x: (x.name or ""))],
    }
    return JsonResponse(payload)



def _mastery_state(character, subclass, modules_per_mastery: int) -> dict:
    """
    Returns: {
      "taken": int,  # number of subclass features already taken from this subclass
      "rank": int,   # floor(taken / modules_per_mastery)
      "into_rank": int,         # taken % modules_per_mastery
      "need_for_next": int,     # modules_per_mastery - into_rank (0 if at boundary)
    }
    """
    taken = CharacterFeature.objects.filter(
        character=character,
        subclass=subclass,
        feature__scope='subclass_feat'
    ).count()

    mpm = max(1, int(modules_per_mastery or 1))
    rank = taken // mpm
    into = taken % mpm
    need = (mpm - into) if into else 0
    return {"taken": taken, "rank": rank, "into_rank": into, "need_for_next": need}

# views.py (top, after imports)
def _nonempty(val):
    if isinstance(val, (list, dict, tuple, set)): return bool(val)
    return val not in (None, "")
def _eval_formula(expr, ctx):
    if not expr: return None
    try:
        return int(eval(expr, {"__builtins__": {}}, ctx))
    except Exception:
        return None
# views.py

HIDE_LABELS = {"Scope", "Kind", "Activity", "Activity Type"}  # anything we never want to show

def _feature_details_map(f):
    """
    Build an ordered list of (label, value) for ClassFeature f,
    skipping empty values and hiding Scope/Kind/Activity.
    """
    items = []

    # Basic identity
    items.append(_nonempty_tuple("Code", f.code))
    items.append(_nonempty_tuple("Name", f.name))
    if getattr(f, "character_class", None):
        items.append(_nonempty_tuple("Class", f.character_class.name))
    if getattr(f, "subclass_group", None):
        items.append(_nonempty_tuple("Subclass Group", f.subclass_group.name))
    if getattr(f, "subclasses", None):
        subs = ", ".join(s.name for s in f.subclasses.all())
        items.append(_nonempty_tuple("Subclasses", subs))

    # Level / Tiers / Mastery
    items.append(_nonempty_tuple("Level Required", f.level_required))
    items.append(_nonempty_tuple("Min Class Level", f.min_level))
    items.append(_nonempty_tuple("Tier", f.tier))
    items.append(_nonempty_tuple("Mastery Rank", f.mastery_rank))

    # Action only (NO Activity)
    if getattr(f, "action_type", ""):
        items.append(_nonempty_tuple(
            "Action",
            f.get_action_type_display() if hasattr(f, "get_action_type_display") else f.action_type
        ))

    # Saving Throw
    if getattr(f, "saving_throw_required", False):
        items.append(("Saving Throw Required", "Yes"))
        items.append(_nonempty_tuple(
            "Save Type",
            f.get_saving_throw_type_display() if hasattr(f, "get_saving_throw_type_display") else f.saving_throw_type
        ))
        items.append(_nonempty_tuple(
            "Save Granularity",
            f.get_saving_throw_granularity_display() if hasattr(f, "get_saving_throw_granularity_display") else f.saving_throw_granularity
        ))
        items.append(_nonempty_tuple("Critical Success", f.saving_throw_critical_success))
        items.append(_nonempty_tuple("Success",           f.saving_throw_success or f.saving_throw_basic_success))
        items.append(_nonempty_tuple("Failure",           f.saving_throw_failure or f.saving_throw_basic_failure))
        items.append(_nonempty_tuple("Critical Failure",  f.saving_throw_critical_failure))

    # Damage / Formula
    items.append(_nonempty_tuple(
        "Damage Type",
        f.get_damage_type_display() if hasattr(f, "get_damage_type_display") else f.damage_type
    ))
    items.append(_nonempty_tuple(
        "Formula Target",
        f.get_formula_target_display() if hasattr(f, "get_formula_target_display") else f.formula_target
    ))
    items.append(_nonempty_tuple("Formula", f.formula))
    items.append(_nonempty_tuple("Uses",    f.uses))

    # Proficiency modification (if used)
    items.append(_nonempty_tuple("Modify Proficiency Target", f.modify_proficiency_target))
    items.append(_nonempty_tuple(
        "Modify Proficiency Tier", f.modify_proficiency_amount.name if f.modify_proficiency_amount_id else None
    ))

    # Resistances
    items.append(_nonempty_tuple(
        "Resistance Mode",
        f.get_gain_resistance_mode_display() if hasattr(f, "get_gain_resistance_mode_display") else f.gain_resistance_mode
    ))
    if f.gain_resistance_types:
        items.append(_nonempty_tuple("Resistance Types", ", ".join(f.gain_resistance_types)))
    items.append(_nonempty_tuple("Resistance Amount", f.gain_resistance_amount))

    # Spellcasting entitlements
    items.append(_nonempty_tuple(
        "Spell List",
        f.get_spell_list_display() if hasattr(f, "get_spell_list_display") else f.spell_list
    ))
    items.append(_nonempty_tuple("Cantrips Formula",       f.cantrips_formula))
    items.append(_nonempty_tuple("Spells Known Formula",   f.spells_known_formula))
    items.append(_nonempty_tuple("Spells Prepared Formula",f.spells_prepared_formula))

    # Options (class feature options—not race options)
    if getattr(f, "has_options", False) and f.options.exists():
        labels = [o.label for o in f.options.all()]
        items.append(_nonempty_tuple("Options", ", ".join(labels)))

    # Description
    items.append(_nonempty_tuple("Description", f.description))

    # Filter: drop empties and hidden labels
    items = [p for p in items if p is not None and p[0] not in HIDE_LABELS and p[1] not in (None, "", [], {})]
    return items


def _feat_details_map(feat):
    """
    Conservative: only include keys if they exist on your Feat model.
    """
    out = {}
    for k, label in [
        ("summary", "Summary"),
        ("description", "Description"),
        ("prerequisites", "Prerequisites"),
        ("level_prerequisite", "Level Prerequisite"),
        ("feat_type", "Feat Type"),
        ("tags", "Tags"),
        ("rarity", "Rarity"),
        ("action_type", "Action Type"),
        ("uses", "Uses"),
    ]:
        if hasattr(feat, k):
            v = getattr(feat, k, None)
            if _nonempty(v): out[label] = v
    return out

# --- Build selection blocks for the template ---------------------------------
def _build_spell_selection_blocks(char: Character) -> list[dict]:
    slots_by_origin = _slot_totals_by_origin_and_rank(char)   # origin -> {rank:int -> slots}
    totals = _formula_totals(char)                             # origin -> caps
    # Known spells (cache)
    known_qs = (CharacterKnownSpell.objects
                .filter(character=char)
                .select_related("spell"))
    known_ids = set(known_qs.values_list("spell_id", flat=True))

    # known grouped for prepare choices
    known_by_origin_rank: dict[str, dict[int, list[Spell]]] = {o: {r: [] for r in range(0,11)} for o in ORIGINS}
    for ks in known_qs:
        known_by_origin_rank[ks.origin][ks.rank].append(ks.spell)

    blocks = []
    for feature, cls, cls_level in _active_spell_tables(char):
        origin = (feature.spell_list or "").lower()
        if origin not in ORIGINS:
            continue

        # caps & currents
        can_cap   = int(totals[origin]["cantrips_known"] or 0)
        known_cap = int(totals[origin]["spells_known"] or 0)

        can_current   = CharacterKnownSpell.objects.filter(character=char, origin=origin, rank=0).count()
        known_current = CharacterKnownSpell.objects.filter(character=char, origin=origin).exclude(rank=0).count()

        # needs
        needs_cantrips = max(0, can_cap - can_current)
        needs_known    = max(0, known_cap - known_current) if known_cap else 0

        # choices filtered by Origin
        cantrip_choices = (Spell.objects
                               .filter(level=0, origin__iexact=origin)
                               .exclude(pk__in=known_ids)
                               .order_by("name"))

        # learn-by-level choices filtered by Origin
        slots_map = slots_by_origin.get(origin, {})
        max_rank = max([r for r in range(1,11) if (slots_map.get(r,0) or 0) > 0] or [1])
        spell_choices_by_rank = {
            r: (Spell.objects
                    .filter(level=r, origin__iexact=origin)
                    .exclude(pk__in=known_ids)
                    .order_by("name"))
            for r in range(1, max_rank+1)
        }

        # prepare: remaining and choices (rank 1..10; rank 0 has no slots by default)
        remaining = _spellcasting_context(char)["remaining_slots"][origin]
        prepared_remaining_by_rank = {r: int(remaining.get(r, 0)) for r in range(1, max_rank+1)}
        # include 0 if you enforce a prepared cantrip cap (defaults to 0 = unlimited by slots)
        prepared_remaining_by_rank[0] = int(totals[origin].get("spells_prepared_cap", 0) or 0)

        prepare_choices_by_rank = {r: known_by_origin_rank[origin][r] for r in range(0, max_rank+1)}

        blocks.append(dict(
            feature_id=feature.pk,
            class_name=cls.name,
            origin=origin,
            max_rank=max_rank,
            slots_by_rank=slots_map,
            # cantrips
            known_cantrips_current=can_current,
            cantrips_max=can_cap,
            needs_cantrips=needs_cantrips,
            cantrip_choices=cantrip_choices,
            # known
            known_leveled_current=known_current,
            known_max=known_cap or None,
            needs_known=needs_known,
            spell_choices_by_rank=spell_choices_by_rank,
            # prepare
            prepared_remaining_by_rank=prepared_remaining_by_rank,
            prepare_choices_by_rank=prepare_choices_by_rank,
        ))
    return blocks

def _skill_label(obj) -> str:
    """
    Background.primary/secondary skill can be Skill or SubSkill (GenericFK).
    SubSkill.__str__ returns 'Skill – SubSkill' already; Skill returns 'Skill'.
    """
    if not obj:
        return ""
    try:
        return str(obj)
    except Exception:
        return ""

def _bg_label(bg) -> str:
    """Human-friendly label for dropdowns: shows ability bonuses and proficiencies."""
    if not bg:
        return ""
    prim_abil = bg.get_primary_ability_display()
    sec_abil  = bg.get_secondary_ability_display()
    prim_sk   = _skill_label(bg.primary_skill)
    sec_sk    = _skill_label(bg.secondary_skill)
    return (
        f"{bg.name} — Primary: +{bg.primary_bonus} {prim_abil}"
        f"{' • ' + prim_sk if prim_sk else ''} | "
        f"Secondary: +{bg.secondary_bonus} {sec_abil}"
        f"{' • ' + sec_sk if sec_sk else ''}"
    )

def _fetch_bg(code: str):
    from .models import Background
    if not code:
        return None
    try:
        return Background.objects.get(code=code)
    except Background.DoesNotExist:
        return None


def _is_untrained_name(name: str | None) -> bool:
    return (name or "").strip().lower() == "untrained"

from django.contrib.contenttypes.models import ContentType
# characters/views.py
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Prefetch

@login_required
def character_list(request):
    characters = (
        request.user.characters
        .select_related("race", "subrace", "campaign")
        .prefetch_related(Prefetch("class_progress__character_class"))
        .all()
    )
    return render(request, 'forge/character_list.html', {'characters': characters})

@login_required
@require_POST
def delete_character(request, pk):
    char = get_object_or_404(Character, pk=pk, user=request.user)
    name = char.name
    char.delete()
    messages.success(request, f'Deleted “{name}”.')
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect('characters:character_list')

@login_required
@require_POST
def bulk_delete_characters(request):
    ids = request.POST.getlist("ids") or request.POST.getlist("ids[]")
    qs = Character.objects.filter(user=request.user, id__in=ids)
    count = qs.count()
    qs.delete()
    messages.success(request, f"Deleted {count} character{'s' if count != 1 else ''}.")
    return redirect('characters:character_list')


@login_required
def link_character_to_campaign(request, campaign_id, character_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    character = get_object_or_404(Character, id=character_id, user=request.user)
    # Optionally, check if character is already linked or add validations here
    character.campaign = campaign
    character.save()
    return redirect('campaigns:campaign_detail', campaign_id=campaign.id)

# characters/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CharacterCreationForm, ManualGrantForm, CharacterCreationForm, RemoveItemsForm
import re
from django.views.generic import ListView, DetailView
# views.py
import json
from django.shortcuts import render, redirect
from .forms import CharacterCreationForm

# characters/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import CharacterDetailsForm,ManualGrantForm, CharacterCreationForm
from .models import Armor, Character, CharacterFeat, CharacterManualGrant
from .models import SubSkill, ProficiencyLevel, CharacterSkillProficiency  ,  Weapon, WeaponTraitValue, Armor, CharacterWeaponEquip,CharacterKnownSpell, CharacterPreparedSpell,MartialMastery,CharacterMartialMastery, CharacterActivation
from django.core.exceptions import ValidationError
from django.shortcuts import render
from characters.models import CharacterFieldOverride, CharacterFieldNote, LoremasterArticle,Spell,Subrace, CharacterFeature, ClassFeat,UniversalLevelFeature, CharacterClass, ClassFeature, ClassSubclass, SubclassGroup,  ClassProficiencyProgress, ProficiencyTier, PROFICIENCY_TYPES

from collections import OrderedDict

def _nonempty_tuple(label, value):
    if value is None: 
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return (label, value)

def _feature_details_map(f):
    """
    Build an ordered list of (label, value) for ClassFeature f,
    skipping empty values. Only shows meaningful fields.
    """
    items = []

    # Basic identity
    items.append(_nonempty_tuple("Code", f.code))
    items.append(_nonempty_tuple("Name", f.name))
    if getattr(f, "character_class", None):
        items.append(_nonempty_tuple("Class", f.character_class.name))
    if getattr(f, "subclass_group", None):
        items.append(_nonempty_tuple("Subclass Group", f.subclass_group.name))
    if getattr(f, "subclasses", None):
        subs = ", ".join(s.name for s in f.subclasses.all())
        items.append(_nonempty_tuple("Subclasses", subs))
    items.append(_nonempty_tuple("Scope", f.get_scope_display() if hasattr(f, "get_scope_display") else f.scope))
    items.append(_nonempty_tuple("Kind", f.get_kind_display() if hasattr(f, "get_kind_display") else f.kind))

    # Level / Tiers / Mastery
    items.append(_nonempty_tuple("Level Required", f.level_required))
    items.append(_nonempty_tuple("Min Class Level", f.min_level))
    items.append(_nonempty_tuple("Tier", f.tier))
    items.append(_nonempty_tuple("Mastery Rank", f.mastery_rank))

    # Activation / Action
    if getattr(f, "activity_type", ""):
        items.append(_nonempty_tuple("Activity", f.get_activity_type_display() if hasattr(f, "get_activity_type_display") else f.activity_type))
    if getattr(f, "action_type", ""):
        items.append(_nonempty_tuple("Action", f.get_action_type_display() if hasattr(f, "get_action_type_display") else f.action_type))

    # Saving Throw
    if f.saving_throw_required:
        items.append(("Saving Throw Required", "Yes"))
        items.append(_nonempty_tuple("Save Type", f.get_saving_throw_type_display() if hasattr(f, "get_saving_throw_type_display") else f.saving_throw_type))
        items.append(_nonempty_tuple("Save Granularity", f.get_saving_throw_granularity_display() if hasattr(f, "get_saving_throw_granularity_display") else f.saving_throw_granularity))
        # outcomes
        items.append(_nonempty_tuple("Critical Success", f.saving_throw_critical_success))
        items.append(_nonempty_tuple("Success", f.saving_throw_success or f.saving_throw_basic_success))
        items.append(_nonempty_tuple("Failure", f.saving_throw_failure or f.saving_throw_basic_failure))
        items.append(_nonempty_tuple("Critical Failure", f.saving_throw_critical_failure))

    # Damage / Formula
    items.append(_nonempty_tuple("Damage Type", f.get_damage_type_display() if hasattr(f, "get_damage_type_display") else f.damage_type))
    items.append(_nonempty_tuple("Formula Target", f.get_formula_target_display() if hasattr(f, "get_formula_target_display") else f.formula_target))
    items.append(_nonempty_tuple("Formula", f.formula))
    items.append(_nonempty_tuple("Uses", f.uses))

    # Proficiency modification (if used)
    items.append(_nonempty_tuple("Modify Proficiency Target", f.modify_proficiency_target))
    items.append(_nonempty_tuple("Modify Proficiency Tier", f.modify_proficiency_amount.name if f.modify_proficiency_amount_id else None))

    # Resistances (descriptor only; you’re also using DamageResistance model elsewhere)
    items.append(_nonempty_tuple("Gain Resistance Mode", f.get_gain_resistance_mode_display() if hasattr(f, "get_gain_resistance_mode_display") else f.gain_resistance_mode))
    if f.gain_resistance_types:
        items.append(_nonempty_tuple("Resistance Types", ", ".join(f.gain_resistance_types)))
    items.append(_nonempty_tuple("Resistance Amount", f.gain_resistance_amount))

    # Spellcasting entitlements
    items.append(_nonempty_tuple("Spell List", f.get_spell_list_display() if hasattr(f, "get_spell_list_display") else f.spell_list))
    items.append(_nonempty_tuple("Cantrips Formula", f.cantrips_formula))
    items.append(_nonempty_tuple("Spells Known Formula", f.spells_known_formula))
    items.append(_nonempty_tuple("Spells Prepared Formula", f.spells_prepared_formula))

    # Options
    if f.has_options and f.options.exists():
        labels = [o.label for o in f.options.all()]
        items.append(_nonempty_tuple("Options", ", ".join(labels)))

    # Description (HTML allowed)
    items.append(_nonempty_tuple("Description", f.description))

    items = [p for p in items if p is not None]
    return [(k, v) for (k, v) in items if v not in (None, "", [], {})]
def _feat_details_map(feat):
    items = []
    items.append(_nonempty_tuple("Name", feat.name))
    items.append(_nonempty_tuple("Type", getattr(feat, "feat_type", None)))
    items.append(_nonempty_tuple("Level Prerequisite", getattr(feat, "level_prerequisite", None)))
    items.append(_nonempty_tuple("Class", getattr(feat, "class_name", None)))
    items.append(_nonempty_tuple("Prerequisites", getattr(feat, "prerequisites", None)))
    items.append(_nonempty_tuple("Tags", getattr(feat, "tags", None)))
    items.append(_nonempty_tuple("Description", getattr(feat, "description", None)))

    # NEW: drop Nones first, then filter
    items = [p for p in items if p is not None]
    return [(k, v) for (k, v) in items if v not in (None, "", [], {})]



def _class_level_after_pick(character, base_class):
    """Class-level for the selected class *after* this level-up."""
    prog = character.class_progress.filter(character_class=base_class).first()
    return (prog.levels if prog else 0) + 1
LEVEL_NUM_RE = re.compile(r'(\d+)\s*(?:st|nd|rd|th)?')

def _fmt(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)
def _weapon_trait_names_lower(weapon: Weapon) -> set[str]:
    vals = WeaponTraitValue.objects.filter(weapon=weapon).select_related("trait")
    return { (v.trait.name or "").strip().lower() for v in vals }


def _wtraits_lower(weapon: Weapon) -> set[str]:
    vals = WeaponTraitValue.objects.filter(weapon=weapon).select_related("trait")
    return {(v.trait.name or "").strip().lower() for v in vals}

def _weapon_math(weapon: Weapon, str_mod: int, dex_mod: int, prof_weapon: int, half_lvl_if_trained: int):
    """
    Finesse or ranged → show STR and DEX for hit AND damage
    Balanced        → show STR and DEX for hit, STR only for damage
    Default         → STR only for both
    """
    traits      = _wtraits_lower(weapon)
    is_ranged   = (weapon.range_type or Weapon.MELEE) == Weapon.RANGED
    has_finesse = "finesse" in traits
    has_balanced= "balanced" in traits

    base   = prof_weapon + half_lvl_if_trained
    hit_S  = base + str_mod
    hit_D  = base + dex_mod
    dmg_S  = str_mod
    dmg_D  = dex_mod

    if is_ranged or has_finesse:
        return dict(rule="finesse_or_ranged", show_choice_hit=True,  show_choice_dmg=True,
                    base=base, hit_str=hit_S, hit_dex=hit_D, dmg_str=dmg_S, dmg_dex=dmg_D, traits=sorted(traits))
    if has_balanced:
        return dict(rule="balanced",       show_choice_hit=True,  show_choice_dmg=False,
                    base=base, hit_str=hit_S, hit_dex=hit_D, dmg_str=dmg_S, dmg_dex=dmg_D, traits=sorted(traits))
    return dict(rule="default",            show_choice_hit=False, show_choice_dmg=False,
                base=base, hit_str=hit_S, hit_dex=hit_D, dmg_str=dmg_S, dmg_dex=dmg_D, traits=sorted(traits))


def _weapon_math_for(weapon: Weapon, str_mod: int, dex_mod: int, prof_weapon: int, half_lvl_if_trained: int):
    """
    Returns a dict with hit/damage totals for STR and DEX, plus which are applicable by rules.
    Rules:
      - ranged OR has 'finesse' => use better(STR, DEX) for hit and damage (show both).
      - has 'balanced'          => hit uses better(STR,DEX), damage uses STR (show both for hit only).
      - else                    => STR for both (no choice).
    """
    traits = _weapon_trait_names_lower(weapon)
    is_ranged   = (weapon.range_type or Weapon.MELEE) == Weapon.RANGED
    has_finesse = "finesse" in traits
    has_balanced= "balanced" in traits

    base = prof_weapon + half_lvl_if_trained
    hit_str = base + str_mod
    hit_dex = base + dex_mod
    dmg_str = str_mod
    dmg_dex = dex_mod  # only “applicable” when finesse/ranged allows it

    rule = "default"
    show_choice_hit = False
    show_choice_dmg = False

    if is_ranged or has_finesse:
        rule = "finesse_or_ranged"
        show_choice_hit = True
        show_choice_dmg = True
    elif has_balanced:
        rule = "balanced"
        show_choice_hit = True
        show_choice_dmg = False
    # else: default STR only

    return {
        "rule": rule,
        "show_choice_hit": show_choice_hit,
        "show_choice_dmg": show_choice_dmg,
        "hit_str": hit_str,
        "hit_dex": hit_dex,
        "dmg_str": dmg_str,
        "dmg_dex": dmg_dex,
        "base": base,
        "traits": sorted(list(traits)),
    }

@login_required
@require_POST
def set_weapon_choice(request, pk):
    character = get_object_or_404(Character, pk=pk, user=request.user)
    raw_slot  = (request.POST.get("slot") or "").strip().lower()   # accepts "1/2/3" or "primary/secondary/tertiary"
    weapon_id = (request.POST.get("weapon_id") or "").strip()

    slot_map = {"1":1,"2":2,"3":3,"primary":1,"secondary":2,"tertiary":3}
    slot_index = slot_map.get(raw_slot)
    if slot_index not in (1,2,3):
        return HttpResponseBadRequest("Invalid slot")

    if weapon_id == "":
        CharacterWeaponEquip.objects.filter(character=character, slot_index=slot_index).delete()
        return JsonResponse({"ok": True})

    try:
        weapon = Weapon.objects.get(pk=int(weapon_id))
    except (ValueError, Weapon.DoesNotExist):
        return HttpResponseBadRequest("Invalid weapon_id")

    CharacterWeaponEquip.objects.update_or_create(
        character=character, slot_index=slot_index, defaults={"weapon": weapon}
    )
    return JsonResponse({"ok": True})


def _current_proficiencies_for_character(character):
    """
    For each PROFICIENCY_TYPES code, find the best (highest-bonus) ProficiencyTier
    unlocked across all of the character's class_progress rows.
    'modifier' here = ProficiencyTier.bonus (no ability added).
    """
    out = []
    label_by_code = dict(PROFICIENCY_TYPES)
    cps = (character.class_progress
                      .select_related('character_class')
                      .all())

    for code in label_by_code.keys():
        best_tier = None
        best_row  = None
        for cp in cps:
            qs = (ClassProficiencyProgress.objects
                    .select_related('tier')
                    .filter(character_class=cp.character_class,
                            proficiency_type=code,
                            at_level__lte=cp.levels))
            for row in qs:
                t = row.tier
                if (best_tier is None) or (t.bonus > best_tier.bonus):
                    best_tier = t
                    best_row  = row

        out.append({
            "type_code":  code,
            "type_label": label_by_code[code],
            "tier_name":  best_tier.name if best_tier else "—",
            "modifier":   best_tier.bonus if best_tier else 0,
            "source":     (f"{best_row.character_class.name} L{best_row.at_level}"
                           if best_row else "—"),
        })
    return out

def _half_level_total(level: int) -> int:
    return math.ceil(level / 2)


@login_required
@require_POST
def set_activation(request, pk):
    character = get_object_or_404(Character, pk=pk, user=request.user)
    ctype_id  = request.POST.get("ctype")
    obj_id    = request.POST.get("obj")
    active    = (request.POST.get("active") == "1")
    note      = (request.POST.get("note") or "").strip()

    try:
        ct = ContentType.objects.get_for_id(int(ctype_id))
        oid = int(obj_id)
    except (ValueError, ContentType.DoesNotExist):
        return HttpResponseBadRequest("Bad target")

    rec, _ = CharacterActivation.objects.update_or_create(
        character=character, content_type=ct, object_id=oid,
        defaults={"is_active": active, "note": note}
    )
    return JsonResponse({"ok": True, "active": rec.is_active})

# characters/views.py  — spellcasting bits that match your models/admin/urls

from collections import defaultdict, Counter
import ast
from typing import Dict, Any

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import (
    Character, CharacterClassProgress, CharacterClass, ClassFeature, SpellSlotRow,
    Spell, CharacterKnownSpell, CharacterPreparedSpell
)

ORIGINS = ["arcane", "divine", "primal", "occult"]
RANKS   = list(range(0, 11))  # 0 = cantrips, 1..10 = slots

# ----------------------------- helpers ---------------------------------

def _char_or_403(request, pk: int) -> Character:
    c = get_object_or_404(Character, pk=pk)
    if not request.user.is_superuser and c.user_id != request.user.id:
        raise HttpResponseForbidden("Not your character.")
    return c

def _safe_eval(expr: str, variables: Dict[str, Any]) -> int:
    """
    Super-small “safe eval”: allow only ints, + - * // / % ** ( ) and variable names
    present in `variables`. Supports ceil/floor and friendly 'round up/down' variants.
    Returns an int >= 0.
    """
    if not expr:
        return 0

    # Normalize friendly syntax to valid Python function names
    s = expr.strip()
    s = re.sub(r'\bround\s*up\s*\(', 'ceil(', s, flags=re.I)
    s = re.sub(r'\bround\s*down\s*\(', 'floor(', s, flags=re.I)
    s = re.sub(r'\bround_up\s*\(', 'ceil(', s, flags=re.I)
    s = re.sub(r'\bround_down\s*\(', 'floor(', s, flags=re.I)

    node = ast.parse(s, mode="eval")

    allowed_nodes = (
        ast.Expression, ast.BinOp, ast.UnaryOp,
        ast.Num, ast.Constant, ast.Load, ast.Name,
        ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Div, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd, ast.Call
    )
    allowed_funcs = {
        "floor": lambda x: int(math.floor(x)),
        "ceil":  lambda x: int(math.ceil(x)),
        "min":   min,
        "max":   max,
        "round": lambda x: int(round(x)),
    }

    def _eval(n):
        if not isinstance(n, allowed_nodes):
            raise ValueError("Illegal expression.")
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Num):
            return n.n
        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)): return n.value
            raise ValueError("Illegal literal.")
        if isinstance(n, ast.Name):
            return int(variables.get(n.id, 0))
        if isinstance(n, ast.BinOp):
            left, right = _eval(n.left), _eval(n.right)
            if isinstance(n.op, ast.Add):      return left + right
            if isinstance(n.op, ast.Sub):      return left - right
            if isinstance(n.op, ast.Mult):     return left * right
            if isinstance(n.op, ast.FloorDiv): return left // right
            if isinstance(n.op, ast.Div):      return left / right   
            if isinstance(n.op, ast.Mod):      return left % right
            if isinstance(n.op, ast.Pow):      return int(pow(left, right))
        if isinstance(n, ast.UnaryOp):
            val = _eval(n.operand)
            if isinstance(n.op, ast.UAdd): return +val
            if isinstance(n.op, ast.USub): return -val
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name): raise ValueError("Illegal call.")
            fname = n.func.id
            if fname not in allowed_funcs:      raise ValueError(f"Illegal function {fname}.")
            args = [_eval(a) for a in n.args]
            return int(allowed_funcs[fname](*args))
        raise ValueError("Illegal expression.")

    try:
        return max(0, int(_eval(node)))
    except Exception:
        return 0


def _ability_mod(score: int) -> int:
    try:
        return (int(score) - 10) // 2
    except Exception:
        return 0

def _base_vars_for_character(char: Character) -> Dict[str, Any]:
    str_score = int(char.strength or 0)
    dex_score = int(char.dexterity or 0)
    con_score = int(char.constitution or 0)
    int_score = int(char.intelligence or 0)
    wis_score = int(char.wisdom or 0)
    cha_score = int(char.charisma or 0)

    # Modifiers
    str_mod = _ability_mod(str_score)
    dex_mod = _ability_mod(dex_score)
    con_mod = _ability_mod(con_score)
    int_mod = _ability_mod(int_score)
    wis_mod = _ability_mod(wis_score)
    cha_mod = _ability_mod(cha_score)    
    v = dict(
        level=int(char.level or 0),
        class_level=int(char.level or 0),  # overwritten per-class when evaluating
        proficiency_modifier=0,            # fill with your own calc if you add it
        hp=int(char.HP or 0),
        temp_hp=int(char.temp_HP or 0),
       strength=str_mod, dexterity=dex_mod, constitution=con_mod,
        intelligence=int_mod, wisdom=wis_mod, charisma=cha_mod,

        # Short aliases
        str=str_mod, dex=dex_mod, con=con_mod, int=int_mod, wis=wis_mod, cha=cha_mod,

        # Explicit modifier names (back-compat)
        strength_modifier=str_mod, dexterity_modifier=dex_mod, constitution_modifier=con_mod,
        intelligence_modifier=int_mod, wisdom_modifier=wis_mod, charisma_modifier=cha_mod,

        # Explicit score names still available if ever needed
        strength_score=str_score, dexterity_score=dex_score, constitution_score=con_score,
        intelligence_score=int_score, wisdom_score=wis_score, charisma_score=cha_score,
    )

    # Per-class level variables like "<classname>_level"
    for cp in char.class_progress.select_related("character_class").all():
        key = f"{cp.character_class.name.lower()}_level".replace(" ", "_")
        v[key] = int(cp.levels or 0)

    return v

def _class_level(char: Character, cls: CharacterClass) -> int:
    return int(
        char.class_progress.filter(character_class=cls).values_list("levels", flat=True).first()
        or 0
    )

def _active_spell_tables(char: Character):
    """
    Returns all spell_table features that actually apply to the character
    (class has at least 1 level, and any level_required is met).
    """
    features = []
    for cp in char.class_progress.select_related("character_class"):
        lvl = int(cp.levels or 0)
        if lvl <= 0:
            continue
        tables = ClassFeature.objects.filter(
            character_class=cp.character_class,
            kind="spell_table"
        )
        for f in tables:
            if f.level_required and lvl < f.level_required:
                continue
            features.append((f, cp.character_class, lvl))
    return features

def _slot_totals_by_origin_and_rank(char):
    out = {o: {r: 0 for r in RANKS} for o in ORIGINS}
    for feature, _cls, cls_level in _active_spell_tables(char):
        origin = (feature.spell_list or "").lower()
        if origin not in ORIGINS:
            continue
        row = (feature.spell_slot_rows
                 .filter(level__lte=cls_level)
                 .order_by('-level')
                 .first())
        if not row:
            continue
        for r in range(1, 11):
            out[origin][r] += getattr(row, f"slot{r}", 0) or 0
    return out


def _formula_totals(char: Character) -> Dict[str, Dict[str, int]]:
    """
    Compute per-origin totals from formulas on each applicable spell_table feature:
      - cantrips_known
      - spells_known
      - spells_prepared_cap (if you use it; optional)
    """
    totals = {o: dict(cantrips_known=0, spells_known=0, spells_prepared_cap=0) for o in ORIGINS}
    base_vars = _base_vars_for_character(char)

    for feature, cls, cls_level in _active_spell_tables(char):
        local_vars = dict(base_vars)
        local_vars["class_level"] = cls_level

        origin = (feature.spell_list or "").lower()
        if origin not in ORIGINS:
            continue

        if feature.cantrips_formula:
            totals[origin]["cantrips_known"] += _safe_eval(feature.cantrips_formula, local_vars)
        if feature.spells_known_formula:
            totals[origin]["spells_known"] += _safe_eval(feature.spells_known_formula, local_vars)
        if feature.spells_prepared_formula:
            totals[origin]["spells_prepared_cap"] += _safe_eval(feature.spells_prepared_formula, local_vars)

    return totals

def _prepared_counts(char: Character) -> Dict[str, Counter]:
    """
    Number of prepared spells per origin per rank (rank 0 ignored).
    """
    out = {o: Counter() for o in ORIGINS}
    for ps in char.prepared_spells.select_related("spell"):
        if ps.rank > 0:
            out[ps.origin][ps.rank] += 1
    return out

def _norm_origin(v: str) -> str:
    v = (v or "").strip().lower()
    return v or "—"

def _known_sets(char):
    known_by_origin    = defaultdict(list)
    cantrips_by_origin = defaultdict(list)

    qs = char.known_spells.select_related("spell")
    for ks in qs:
        sp = ks.spell
        rank   = getattr(ks, "rank", getattr(sp, "level", 0)) or 0
        origin = _norm_origin(
            getattr(ks, "origin", None) or getattr(sp, "origin", None) or getattr(sp, "sub_origin", None)
        )
        (cantrips_by_origin if rank == 0 else known_by_origin)[origin].append(ks)

    # if callers expect plain dicts:
    return dict(known_by_origin), dict(cantrips_by_origin)
# --- at top of the helper (or right before you use any origins) ---
from collections import defaultdict

def _okey(v: str) -> str:
    """Normalize any origin/list label into a stable dict key."""
    v = (v or "").strip().lower()
    return v or "—"   # match your view/template fallback

def _spellcasting_context(char):
    # 1) Build prepared counts by normalized (origin, rank)
    prepared_counts = defaultdict(lambda: defaultdict(int))
    max_rank_seen = 0
    for ps in char.prepared_spells.select_related("spell"):
        # prefer row.origin, but fall back to spell-origin if row is blank
        o = _okey(getattr(ps, "origin", None)
                  or getattr(ps.spell, "origin", None)
                  or getattr(ps.spell, "sub_origin", None))
        r = int(getattr(ps, "rank", getattr(ps.spell, "level", 0)) or 0)
        if r > 0:
            prepared_counts[o][r] += 1
            max_rank_seen = max(max_rank_seen, r)

    # 2) Known spells by origin (you only need this if you expose it in scx)
    known_by_origin    = defaultdict(list)
    cantrips_by_origin = defaultdict(list)
    for ks in char.known_spells.select_related("spell"):
        sp = ks.spell
        o = _okey(getattr(ks, "origin", None) or sp.origin or sp.sub_origin)
        r = int(getattr(ks, "rank", getattr(sp, "level", 0)) or 0)
        (cantrips_by_origin if r == 0 else known_by_origin)[o].append(ks)
        max_rank_seen = max(max_rank_seen, r)

    # 3) Slots by origin/rank from your active spell tables (if you have them)
    slots_by_origin_rank = defaultdict(dict)
    for feature, cls, _cls_level in _active_spell_tables(char):  # keep your existing helper
        token = _okey(getattr(feature, "get_spell_list_display", lambda: None)() or feature.spell_list)
        row = feature.spell_slot_rows.filter(level=_cls_level).first()
        if not row:
            continue
        slots = [row.slot1,row.slot2,row.slot3,row.slot4,row.slot5,
                 row.slot6,row.slot7,row.slot8,row.slot9,row.slot10]
        for i, s in enumerate(slots, start=1):
            if s:
                slots_by_origin_rank[token][i] = int(s)
                max_rank_seen = max(max_rank_seen, i)

    # 4) Build the canonical origin set (normalized) so comprehensions can’t KeyError
    all_origins = set(prepared_counts.keys()) | set(known_by_origin.keys()) \
                  | set(cantrips_by_origin.keys()) | set(slots_by_origin_rank.keys())
    if not all_origins:
        all_origins = {"—"}  # at least one key so templates don’t explode

    rank_range = list(range(0, max(1, max_rank_seen) + 1))  # include 0 for cantrips

    # 5) Safely project nested dicts (use .get(...) everywhere)
    prepared_counts_safe = {
        o: {r: int(prepared_counts.get(o, {}).get(r, 0)) for r in rank_range}
        for o in all_origins
    }
    slots_safe = {
        o: {r: int(slots_by_origin_rank.get(o, {}).get(r, 0)) for r in rank_range if r > 0}
        for o in all_origins
    }

    remaining_slots = {o: {} for o in all_origins}
    for o in all_origins:
        for r in rank_range:
            if r == 0:
                continue
            total = int(slots_safe.get(o, {}).get(r, 0))
            used  = int(prepared_counts_safe.get(o, {}).get(r, 0))
            remaining_slots[o][r] = max(0, total - used)

    return {
        "rank_range": rank_range,
        "prepared_counts": prepared_counts_safe,
        "known_by_origin": dict(known_by_origin),
        "cantrips_by_origin": dict(cantrips_by_origin),
        "slots_by_origin_rank": slots_safe,
        "remaining_slots": remaining_slots,           # ← restore this
        "origins": sorted(all_origins),
    }

# ----------------------------- page views --------------------------------
# characters/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.urls import reverse
import re

from .models import ClassFeat

# Split "Wizard, Fighter / Ranger; Rogue" → ["Wizard","Fighter","Ranger","Rogue"]
_TOKEN_SPLIT_RE = re.compile(r"\s*[,;/|]\s*")
def _tokens(s: str | None) -> list[str]:
    if not s:
        return []
    return [t.strip() for t in _TOKEN_SPLIT_RE.split(s) if t.strip()]

# Your helper from above; keep as-is if already defined
LEVEL_NUM_RE = re.compile(r'(\d+)\s*(?:st|nd|rd|th)?')
def parse_req_level(txt: str | None) -> int:
    if not txt:
        return 0
    nums = [int(n) for n in LEVEL_NUM_RE.findall(txt)]
    return min(nums) if nums else 0

def feat_list(request):
    # Just render the page; JS will fetch data from feat_data()
    return render(request, "codex/feat_list.html", {
        "data_url": reverse("feat_data"),
    })

def feat_data(request):
    """
    Lightweight JSON for client-side filtering.
    Tokenizes class_name and race columns so filters match each value correctly.
    """
    rows = []
    for f in ClassFeat.objects.all().order_by("name"):
        feat_types = [t.strip() for t in (f.feat_type or "").split(",") if t.strip()]
        class_vals = _tokens(f.class_name)
        race_vals  = _tokens(f.race)
        tag_vals   = [t.strip() for t in (f.tags or "").split(",") if t.strip()]
        rows.append({
            "id": f.id,
            "name": f.name or "",
            "feat_type_raw": f.feat_type or "",
            "feat_types": feat_types,                 # e.g. ["Class"]
            "class_tokens": class_vals,               # ["Wizard","Fighter","Ranger"]
            "race_tokens": race_vals,                 # ["Elf","Dwarf"]
            "tags": tag_vals,                         # ["Focus","Defense"]
            "level_req_num": parse_req_level(getattr(f, "level_prerequisite", "")),
            "level_prereq_raw": getattr(f, "level_prerequisite", "") or "",
            "prerequisites": getattr(f, "prerequisites", "") or "",
            "description": getattr(f, "description", "") or "",
        })
    return JsonResponse({"feats": rows})


# characters/views.py  (replace your spell_list with this version)

ORIGINS = ["arcane", "divine", "primal", "occult"]
# characters/views.py
ORIGINS = ["arcane", "divine", "primal", "occult"]

# views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Spell

ORIGINS = ["arcane", "divine", "primal", "occult"]

@login_required
def spell_list(request):
    qs = Spell.objects.all().order_by("level", "name")

    # Build JSON rows for the client grid (drawer + per-column filters)
    spells_json = []
    for s in qs:
        # tags split once here so the template doesn't need custom filters
        tag_list = [t.strip() for t in (s.tags or "").split(",") if t.strip()]
        spells_json.append({
            "id": s.id,
            "name": s.name or "",
            "level": int(s.level or 0),
            "origin": (s.origin or "").strip(),         # keep raw; JS will tokenize
            "classification": (s.classification or "").strip(),
            "tags": tag_list,
            "casting_time": s.casting_time or "",
            "duration": s.duration or "",
            "components": s.components or "",
            "range": s.range or "",
            "target": s.target or "",
            "sub_origin": s.sub_origin or "",
            "saving_throw": s.saving_throw or "",
            "effect": s.effect or "",
            "upcast_effect": s.upcast_effect or "",
            "last_synced": (s.last_synced.isoformat() if getattr(s, "last_synced", None) else ""),
        })

    return render(request, "codex/spell_list.html", {
        "spells_json": spells_json,
        "levels": list(range(0, 11)),   # Cantrip (0) … 10
        "origins": ORIGINS,             # seed only; menus populate from data too
    })




# --------------------------- AJAX mutations -------------------------------

@login_required
@require_POST
@transaction.atomic
def add_known_spell(request, pk: int):
    """
    POST fields:
      - spell_id (required)
      - origin   (arcane/divine/primal/occult; required)
      - rank     (0..10; optional → default to Spell.level)
      - from_class_id (optional)
    Enforces per-origin known-spell cap from feature formulas.
    """
    char = _char_or_403(request, pk)
    spell_id = request.POST.get("spell_id")
    origin   = (request.POST.get("origin") or "").lower()
    rank_str = request.POST.get("rank")
    from_class_id = request.POST.get("from_class_id")

    if origin not in ORIGINS:
        return HttpResponseBadRequest("Invalid origin.")
    spell = get_object_or_404(Spell, pk=spell_id)
    rank = int(rank_str) if (rank_str and rank_str.isdigit()) else int(spell.level or 0)

    if CharacterKnownSpell.objects.filter(character=char, spell=spell).exists():
        return JsonResponse({"ok": True, "message": "Already known.", "spellcasting": _spellcasting_context(char)})

    # enforce known cap (excluding cantrips from the cap by convention; tweak if you want)
    totals = _formula_totals(char)
    cap = int(totals[origin]["spells_known"])
    current_known = CharacterKnownSpell.objects.filter(character=char, origin=origin).exclude(rank=0).count()
    if rank > 0 and cap and current_known >= cap:
        return JsonResponse({"ok": False, "error": "Known spell limit reached for this origin."}, status=400)

    from_class = None
    if from_class_id and from_class_id.isdigit():
        from_class = CharacterClass.objects.filter(pk=int(from_class_id)).first()

    CharacterKnownSpell.objects.create(
        character=char, spell=spell, origin=origin, rank=rank, from_class=from_class
    )
    return JsonResponse({"ok": True, "spellcasting": _spellcasting_context(char)})

@login_required
@require_POST
@transaction.atomic
def set_prepared_spell(request, pk: int):
    """
    Toggle prepare/unprepare.
    POST fields:
      - spell_id (required)
      - origin   (required)
      - rank     (required, 0..10)
      - action   ("prepare" or "unprepare"), default: toggle
    Enforces slot totals per origin/rank from SpellSlotRow. Cantrips (rank 0) do NOT consume slots.
    """
    char = _char_or_403(request, pk)
    spell_id = request.POST.get("spell_id")
    origin   = (request.POST.get("origin") or "").lower()
    rank_str = request.POST.get("rank")
    action   = (request.POST.get("action") or "").lower()

    if origin not in ORIGINS:
        return HttpResponseBadRequest("Invalid origin.")
    if not (rank_str and rank_str.isdigit()):
        return HttpResponseBadRequest("Missing rank.")
    rank = int(rank_str)

    spell = get_object_or_404(Spell, pk=spell_id)

    # Must be known first (except inherent/class-granted logic—adapt if needed)
    if not CharacterKnownSpell.objects.filter(character=char, spell=spell).exists():
        return JsonResponse({"ok": False, "error": "You must learn the spell first."}, status=400)

    existing = CharacterPreparedSpell.objects.filter(character=char, spell=spell, origin=origin, rank=rank)

    # Unprepare logic
    if action == "unprepare" or (not action and existing.exists()):
        existing.delete()
        return JsonResponse({"ok": True, "spellcasting": _spellcasting_context(char)})

    # Prepare logic
    if rank == 0:
        # By convention: cantrips do not consume slots. If you want a cap, enforce with spells_prepared_formula.
        CharacterPreparedSpell.objects.get_or_create(character=char, spell=spell, origin=origin, rank=rank)
        return JsonResponse({"ok": True, "spellcasting": _spellcasting_context(char)})

    # Enforce slots for rank 1..10
    remaining = _spellcasting_context(char)["remaining_slots"]
    if remaining.get(origin, {}).get(rank, 0) <= 0:
        return JsonResponse({"ok": False, "error": "No remaining slots at that rank."}, status=400)

    CharacterPreparedSpell.objects.get_or_create(character=char, spell=spell, origin=origin, rank=rank)
    return JsonResponse({"ok": True, "spellcasting": _spellcasting_context(char)})

@login_required
@require_POST
def pick_martial_mastery(request, pk):
    character = get_object_or_404(Character, pk=pk, user=request.user)
    mastery_id = request.POST.get("mastery_id")
    try:
        mm = MartialMastery.objects.get(pk=int(mastery_id))
    except (ValueError, MartialMastery.DoesNotExist):
        return HttpResponseBadRequest("Invalid mastery_id")

    CharacterMartialMastery.objects.get_or_create(
        character=character, mastery=mm,
        defaults={"level_picked": character.level}
    )
    return JsonResponse({"ok": True})

@login_required
@require_POST
def set_armor_choice(request, pk):
    character = get_object_or_404(Character, pk=pk, user=request.user)
    armor_id = (request.POST.get("armor_id") or "").strip()

    # Clear equipped armor
    if armor_id == "":
        CharacterFieldOverride.objects.filter(character=character, key="equipped_armor_id").delete()
        CharacterFieldOverride.objects.filter(character=character, key="armor_value").delete()
        return JsonResponse({"ok": True})

    # Set equipped armor by id
    try:
        armor = Armor.objects.get(pk=int(armor_id))
    except (ValueError, Armor.DoesNotExist):
        return HttpResponseBadRequest("Invalid armor_id")

    CharacterFieldOverride.objects.update_or_create(
        character=character, key="equipped_armor_id", defaults={"value": str(armor.id)}
    )
    CharacterFieldOverride.objects.update_or_create(
        character=character, key="armor_value", defaults={"value": str(armor.armor_value)}
    )
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect('characters:character_detail', pk=pk)
def _fmt(n) -> str:
    try:
        return f"{int(n):+d}"
    except Exception:
        return "0"
def _abil_mod(score: int) -> int:
    # 5e style
    return (score - 10) // 2

def parse_req_level(txt: str | None) -> int:
    if not txt:
        return 0
    nums = [int(n) for n in LEVEL_NUM_RE.findall(txt)]
    return min(nums) if nums else 0
def _unlocked_tiers(group, new_cls_level):
    """
    Which tiers are unlocked for this SubclassGroup at the given class-level?
    Uses SubclassTierLevel rows. If none exist, falls back to 'all tiers ≤ class level'.
    """
    tiers = set(
        group.tier_levels.filter(unlock_level__lte=new_cls_level)
                         .values_list("tier", flat=True)
    )
    if tiers:
        return tiers
    # Fallback: allow tiers up to class level (you can pick a stricter rule if you like)
    return set(range(1, new_cls_level + 1))

def _taken_tier_by_subclass(character, group):
    """
    For each subclass in this group, what's the highest tier the character already has?
    Returns {subclass_id: max_tier_int}
    """
    rows = (
        CharacterFeature.objects
        .filter(
            character=character,
            feature__scope="subclass_feat",
            feature__subclass_group=group,
            subclass__isnull=False,
        )
        .values("subclass_id")
        .annotate(max_tier=Max("feature__tier"))
    )
    return {r["subclass_id"]: (r["max_tier"] or 0) for r in rows}






WORD_BOUNDARY = r'\b{}\b'

def feat_list(request):
    feats = ClassFeat.objects.all()

    q = (request.GET.get('q') or '').strip()
    if q:
        feats = feats.filter(Q(name__icontains=q) | Q(tags__icontains=q))

    type_vals = [t.strip() for t in request.GET.getlist('type') if t.strip()]
    if type_vals:
        ors = [Q(feat_type__iregex=WORD_BOUNDARY.format(re.escape(t))) for t in type_vals]
        from functools import reduce
        feats = feats.filter(reduce(lambda a, b: a | b, ors))

    cls = (request.GET.get('class') or '').strip()
    if cls:
        feats = feats.filter(class_name__iregex=WORD_BOUNDARY.format(re.escape(cls)))

    rc = (request.GET.get('race') or '').strip()
    if rc:
        feats = feats.filter(race__iregex=WORD_BOUNDARY.format(re.escape(rc)))

    feats = list(feats.order_by('name'))

    # Provide a pre-split tag list for pills (avoids .split in template)
    for f in feats:
        f.tag_list = [t.strip() for t in (f.tags or '').split(',') if t.strip()]

    # Also provide a plain list for the three feat-type checkboxes
    feat_type_options = ["General", "Class", "Skill"]

    # (unchanged helper sets, optional for other UI pieces)
    types = sorted(set(cf.feat_type for cf in feats if cf.feat_type))

    raw_feat_types = [cf.feat_type or "" for cf in feats]
    feat_types = sorted({
        part.strip()
        for full in raw_feat_types
        for part in full.split(',')
        if part.strip()
    })

    raw_classes = [cf.class_name or "" for cf in feats]
    class_names = sorted({
        part.strip()
        for full in raw_classes
        for part in full.split(',')
        if part.strip()
    })

    raw_races = [cf.race or "" for cf in feats]
    race_names = sorted({
        part.strip()
        for full in raw_races
        for part in full.split(',')
        if part.strip()
    })

    return render(request, 'codex/feat_list.html', {
        'feats': feats,
        'types': types,
        'feat_types': feat_types,
        'class_names': class_names,
        'race_names': race_names,
        'feat_type_options': feat_type_options,   # ← NEW
        'selected_types': type_vals,
        'selected_class': cls,
        'selected_race': rc,
        'query': q,
    })

def codex_index(request):
    return render(request, 'codex/codex_index.html')


def class_list(request):
    classes = CharacterClass.objects.all().order_by('name')
    return render(request, 'codex/class_list.html', {'classes': classes})

class LoremasterListView(ListView):
    model               = LoremasterArticle
    template_name       = "loremaster/loremaster_list.html"
    context_object_name = "articles"
    paginate_by         = 10

    def get_queryset(self):
        qs = super().get_queryset().filter(published=True)
        q  = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(title__icontains=q) | qs.filter(excerpt__icontains=q)
        return qs


class LoremasterDetailView(DetailView):
    model         = LoremasterArticle
    template_name = "loremaster/loremaster_detail.html"
    context_object_name = "article"

    # will look up by slug because of the URLconf above


def class_subclass_list(request):
    subclasses = ClassSubclass.objects.select_related('base_class').order_by('base_class__name', 'name')
    return render(request, 'codex/subclasses.html', {'subclasses': subclasses})

def subclass_group_list(request):
    groups = SubclassGroup.objects.select_related('character_class').order_by('character_class__name', 'name')
    return render(request, 'codex/groups.html', {'groups': groups})

from collections import OrderedDict

from characters.models import CharacterClass, ClassFeature, ClassSubclass, SubclassGroup, ClassLevel, ClassLevelFeature
def weapon_list(request):
    trait_values_qs = WeaponTraitValue.objects.select_related("trait").order_by("trait__name")
    weapons = (
        Weapon.objects
        .all()
        .prefetch_related(Prefetch("weapontraitvalue_set", queryset=trait_values_qs))
        .order_by("category", "range_type", "name")
    )
    return render(request, "codex/codex_weapons.html", {"weapons": weapons})

# armor: sort by type → armor_value → name (table looks nicer this way)
def armor_list(request):
    armor_items = (
        Armor.objects
        .all()
        .prefetch_related("traits")
        .order_by("type", "armor_value", "name")
    )
    return render(request, "codex/codex_armor.html", {"armor_items": armor_items})


from django.db.models import Prefetch,Max
def class_detail(request, pk):
    cls = get_object_or_404(CharacterClass, pk=pk)

    # ── 1) Proficiency pivot ────────────────────────────────────────────────────
    profs = list(
        cls.prof_progress
           .select_related('tier')
           .order_by('proficiency_type', 'tier__bonus')
    )
    tiers = sorted({p.tier for p in profs}, key=lambda t: t.bonus)
    tier_names = [t.name for t in tiers]

    prof_types = []
    for p in profs:
        lbl = p.get_proficiency_type_display()
        if lbl not in prof_types:
            prof_types.append(lbl)

    # build matrix[proficiency_name][tier_name] = at_level
    matrix = {pt: {tn: None for tn in tier_names} for pt in prof_types}
    for p in profs:
        matrix[p.get_proficiency_type_display()][p.tier.name] = p.at_level

    prof_rows = [
        {'type': pt, 'levels': [matrix[pt][tn] for tn in tier_names]}
        for pt in prof_types
    ]

    # ── 2) Hit die ─────────────────────────────────────────────────────────────
    hit_die = cls.hit_die

    # ── 3) Base‐class features by level ────────────────────────────────────────
    levels = (
        ClassLevel.objects
          .filter(character_class=cls)
          .order_by('level')
          .prefetch_related(
              Prefetch(
                  'features',
                  queryset=ClassFeature.objects
                    .select_related('modify_proficiency_amount')
                    .prefetch_related(
                        'subclasses',
                        'options__grants_feature',   
                    ),
              )
          )
    )

    # Build a per-level list that EXCLUDES features granted by options on the same level.
    for cl in levels:
        feats = list(cl.features.all())
        # All grant targets reachable from features at THIS level:
        granted_ids = {
            opt.grants_feature_id
            for f in feats
            for opt in getattr(f, "options", []).all()
            if opt.grants_feature_id
        }
        # Store both for the template:
        cl._granted_feature_ids = granted_ids
        cl.filtered_features = [f for f in feats if f.id not in granted_ids]

    # Load each group & its subclasses
    subclass_groups = (
        cls.subclass_groups
           .order_by('name')
           .prefetch_related('subclasses')
    )

    # For each individual subclass, build its own level→features map
    # For each individual subclass, build its own level→features map
    for group in subclass_groups:
        # pre‐build a map tier→unlock_level, if needed
        tier_map = {}
        if group.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
            tier_map = {
                tl.tier: tl.unlock_level
                for tl in group.tier_levels.all()
            }

        for sub in group.subclasses.all():
            fbylevel = {}

            if group.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
                # pull all the subclass_feats for this sub, then map by tier→unlock_level
                modular_feats = (
                    ClassFeature.objects
                    .filter(scope='subclass_feat',
                            subclasses=sub,
                            subclass_group=group)
                    .select_related('modify_proficiency_amount')
                    .prefetch_related('options__grants_feature')
                )
                for f in modular_feats:
                    lvl = tier_map.get(f.tier)
                    if lvl:
                        fbylevel.setdefault(lvl, []).append(f)

            elif group.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
                # ⬅️ NEW: mastery modules have no wired ClassLevel; just show them.
                mastery_modules = (
                    ClassFeature.objects
                    .filter(scope='subclass_feat',
                            subclasses=sub,
                            subclass_group=group)
                    .select_related('modify_proficiency_amount')
                    .prefetch_related('options__grants_feature')
                    .order_by('mastery_rank', 'name')
                )
                if mastery_modules:
                    # use a synthetic “level 0” bucket so the template can render them
                    fbylevel[0] = list(mastery_modules)

            else:
                # existing “linear” logic
                for cl in levels:
                    feats = [
                        f for f in cl.features.all()
                        if f.scope == 'subclass_feat' and sub in f.subclasses.all()
                    ]
                    if feats:
                        fbylevel.setdefault(cl.level, []).extend(feats)

            # Sort numerically by the key so 0 (Modules) comes before L2, L5, etc.
            sub.features_by_level = OrderedDict(sorted(fbylevel.items()))

 

    # ── 5) Summary 1…20 ────────────────────────────────────────────────────────
    max_lvl = max(levels.aggregate(Max('level'))['level__max'] or 1, 20)
    summary = []

    for lvl in range(1, max_lvl + 1):
        cl = next((c for c in levels if c.level == lvl), None)
        feats = []
        if cl:
            feats = list(getattr(cl, 'filtered_features', cl.features.all()))

        labels = []
        for f in feats:
            if f.scope == 'subclass_feat':
                names = []
                for sub in f.subclasses.all().select_related('group'):
                    gname = getattr(getattr(sub, "group", None), "name", None)
                    names.append((gname or sub.name or "").strip())
                names = [n for n in names if n]
                labels.append(names[0] if names else (f.name or f.code or "Subclass Feature"))
            else:
                labels.append("–".join(p for p in [f.code, f.name] if p))

        unique = list(dict.fromkeys(labels))  # dedupe, preserve order
        summary.append({'level': lvl, 'features': unique})


    labels = []
    for f in feats:
        if f.scope == 'subclass_feat':
            names = []
            for sub in f.subclasses.all().select_related('group'):
                gname = getattr(getattr(sub, "group", None), "name", None)
                names.append((gname or sub.name or "").strip())
            names = [n for n in names if n]
            labels.append(names[0] if names else (f.name or f.code or "Subclass Feature"))
        else:
            labels.append("–".join(p for p in [f.code, f.name] if p))

        # dedupe, preserve order
        unique = list(dict.fromkeys(labels))
        summary.append({'level': lvl, 'features': unique})

    return render(request, 'codex/class_detail.html', {
        'cls': cls,
        'tier_names': tier_names,
        'prof_rows': prof_rows,
        'hit_die': hit_die,
        'levels': levels,
        'allowed_scopes': ['class_feat', 'subclass_choice'],
        'subclass_groups': subclass_groups,
        'summary': summary,
    })

# characters/views.py

from django.shortcuts import render, get_object_or_404
from .models import CharacterClass, Race




def race_list(request):
    races = Race.objects.all().order_by('name')
    return render(request, 'codex/race_list.html', {'races': races})

from django.shortcuts import get_object_or_404, render
from itertools import groupby
from operator import attrgetter


def race_detail(request, pk):
    race = get_object_or_404(Race, pk=pk)

    feats_qs = (
        race.features
        .select_related('character_class', 'subrace')
        .prefetch_related('gain_subskills', 'race_options__grants_feature', 'spell_slot_rows')
        .order_by('name')
    )

    # (A) Universal = no subrace & no class
    universal_features = [f for f in feats_qs if not f.subrace_id and not f.character_class_id]

    # (B) By Class = has class, but NOT tied to subrace
    class_map = {}
    for f in feats_qs:
        if f.character_class_id and not f.subrace_id:
            class_map.setdefault(f.character_class, []).append(f)

    # (C) By Subrace = any feature where subrace is set (this is now the “subrace feature”)
    subrace_map = {}
    for f in feats_qs:
        if f.subrace_id:
            subrace_map.setdefault(f.subrace, []).append(f)

    # Sort buckets
    universal_features.sort(key=attrgetter('name'))
    for bucket in class_map.values():
        bucket.sort(key=attrgetter('name'))
    for bucket in subrace_map.values():
        bucket.sort(key=attrgetter('name'))

    context = {
        'race': race,
        'universal_features': universal_features,
        'class_features_by_class': sorted(class_map.items(), key=lambda kv: kv[0].name),
        'subrace_features_by_subrace': sorted(subrace_map.items(), key=lambda kv: kv[0].name),
        'subraces': race.subraces.all().order_by('name'),
        'languages': race.languages.all().order_by('name'),
        'tags': race.tags.all().order_by('name'),
    }
    return render(request, 'codex/race_detail.html', context)

# characters/views.py

import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.views.generic import ListView, DetailView
from .models import (
    Race,
    Subrace,
    Background,
    SubSkill,
    ProficiencyLevel,
    CharacterSkillProficiency,
    Rulebook, RulebookPage
)
from .forms import CharacterCreationForm

# characters/views.py

from django.views.generic import ListView, DetailView
from .models import Rulebook, RulebookPage
from django.utils.html import mark_safe

def make_snippet(text: str, query: str, radius: int = 50) -> str:
    """
    Find the first occurrence of query in text, grab up to `radius`
    chars on either side, and wrap the match in <mark>…</mark>.
    """
    idx = text.lower().find(query.lower())
    if idx < 0:
        return ""
    start = max(idx - radius, 0)
    end   = min(idx + len(query) + radius, len(text))
    snippet = text[start:end]
    # escape the query for regex, then wrap each match in <mark>
    pattern = re.escape(query)
    snippet = re.sub(
        rf"({pattern})",
        r"<mark>\1</mark>",
        snippet,
        flags=re.IGNORECASE
    )
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return mark_safe(snippet)

class RulebookListView(ListView):
    model               = Rulebook
    template_name       = "rulebook/list.html"
    context_object_name = "rulebooks"
    paginate_by         = 10

    def get_queryset(self):
        qs = super().get_queryset()
        q  = self.request.GET.get("q", "").strip()
        if q:
            qs = (
                qs.filter(
                    Q(name__icontains=q)         |
                    Q(description__icontains=q)  |
                    Q(pages__title__icontains=q) |
                    Q(pages__content__icontains=q)
                )
                .distinct()
            )
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        results = []
        if q:
            for rb in ctx["rulebooks"]:
                matches = []
                # 1) rulebook.name
                if q.lower() in rb.name.lower():
                    matches.append({
                        "field": "Rulebook Title",
                        "snippet": make_snippet(rb.name, q)
                    })
                # 2) rulebook.description
                if q.lower() in rb.description.lower():
                    matches.append({
                        "field": "Rulebook Description",
                        "snippet": make_snippet(rb.description, q)
                    })
                # 3) each page
                for page in rb.pages.all():
                    if q.lower() in page.title.lower():
                        matches.append({
                            "field": f"Page Title ({page.title})",
                            "snippet": make_snippet(page.title, q)
                        })
                    if q.lower() in page.content.lower():
                        matches.append({
                            "field": f"Page Content ({page.title})",
                            "snippet": make_snippet(page.content, q)
                        })
                if matches:
                    results.append({
                        "rulebook": rb,
                        "matches": matches
                    })
        ctx["results"] = results
        ctx["query"] = q
        return ctx

class RulebookDetailView(DetailView):
    model = Rulebook
    template_name = "rulebook/detail.html"
    context_object_name = "rulebook"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # all pages for this rulebook, ordered by your RulebookPage.order
        ctx['pages'] = self.object.pages.all()
        return ctx




from django.db import transaction

@login_required
def level_down(request, pk):
    character = get_object_or_404(Character, pk=pk, user=request.user)
    if character.level <= 0:
        return redirect('characters:character_detail', pk=pk)

    lvl = character.level

    with transaction.atomic():
        # (A) Snapshot rows for this level BEFORE deleting
        cf_qs = (CharacterFeature.objects
                 .filter(character=character, level=lvl)
                 .select_related('feature', 'feature__character_class'))
        feat_qs = CharacterFeat.objects.filter(character=character, level=lvl)

        # Which class was actually leveled at this character level?
        last_cls_id = (cf_qs.filter(feature__character_class__isnull=False)
                           .order_by('-id')
                           .values_list('feature__character_class_id', flat=True)
                           .first())

        if last_cls_id:
            cp = CharacterClassProgress.objects.filter(
                character=character,
                character_class_id=last_cls_id
            ).first()
        else:
            # Fallback if we have no evidence (dirty data / L1 hiccups)
            cp = character.class_progress.order_by('-levels', '-id').first()

        # (B) Now delete everything granted at this character level
        cf_qs.delete()
        feat_qs.delete()

        # (C) Decrement per-class progress
        if cp:
            cp.levels = models.F('levels') - 1
            cp.save(update_fields=['levels'])
            cp.refresh_from_db()
            if cp.levels <= 0:
                cp.delete()

        # (D) Decrement overall character level
        character.level = lvl - 1
        character.save(update_fields=['level'])

        # (E) Safety net: purge anything that somehow sits above new level
        CharacterFeature.objects.filter(character=character, level__gt=character.level).delete()
        CharacterFeat.objects.filter(character=character, level__gt=character.level).delete()

    return redirect('characters:character_detail', pk=pk)

class RulebookPageDetailView(DetailView):
    model = RulebookPage
    template_name = "rulebook/page_detail.html"
    context_object_name = "page"

@login_required
def create_character(request):
    """
    Stage 1: Name, race, subrace, backgrounds, ability scores, backstory,
    and computed skill proficiencies.
    """
    
    if request.method == 'POST':
        form = CharacterCreationForm(request.POST)
        if form.is_valid():
            # Build but don't save yet; we want to apply background math first.
            character = form.save(commit=False)
            character.user = request.user

            # ---- Resolve Background choices from the form (codes stored in model fields) ----
            main_code = (getattr(character, "main_background", "") or "").strip()
            s1_code   = (getattr(character, "side_background_1", "") or "").strip()
            s2_code   = (getattr(character, "side_background_2", "") or "").strip()

            main_bg = _fetch_bg(main_code)
            side1   = _fetch_bg(s1_code)
            side2   = _fetch_bg(s2_code)

            # ---- Apply Background Rules (server-side backstop) -----------------------------
            # Stacking limit: same ability or skill can only be applied twice total.
            abil_applied_counts = defaultdict(int)   # e.g. "strength" -> 0..2
            abil_adds           = defaultdict(int)   # how much to add to character fields

            def _add_one_abil(abil_key: str) -> bool:
                """Try to add +1 to an ability respecting the 'applied ≤ 2' rule."""
                if not abil_key:
                    return False
                if abil_applied_counts[abil_key] >= 2:
                    return False
                abil_applied_counts[abil_key] += 1
                abil_adds[abil_key] += 1
                return True

            def _add_bonus(abil_key: str, n: int) -> int:
                done = 0
                for _ in range(max(0, n)):
                    if _add_one_abil(abil_key):
                        done += 1
                return done

            # Skills: count how many times each exact Skill/SubSkill was granted (0..2)
            skill_counts = defaultdict(int)  # key=(ctype_id,obj_id) -> 0..2

            from django.contrib.contenttypes.models import ContentType
            from .models import Skill as SkillModel, SubSkill as SubSkillModel

            ct_skill = ContentType.objects.get_for_model(SkillModel)
            ct_sub   = ContentType.objects.get_for_model(SubSkillModel)

            def _skill_key(obj):
                if not obj:
                    return None
                if isinstance(obj, SubSkillModel):
                    return (ct_sub.id, obj.id)
                return (ct_skill.id, obj.id)

            def _grant_skill_once(obj) -> bool:
                key = _skill_key(obj)
                if not key:
                    return False
                if skill_counts[key] >= 2:
                    return False
                skill_counts[key] += 1
                return True

            # ---- Case logic ---------------------------------------------------------------
            # Always aim for: total +3 ability (spread across up to two abilities) and 2 profs.
            # Main Only  => main primary (+2), main secondary (+1); main primary skill AND main secondary skill
            # Main + 1   => main primary (+2) + one +1 from Side (prefer side primary, else side secondary).
            #               Skills: main primary skill + one skill from Side (primary preferred).
            # Main + 2   => main primary (+2) + one +1 from either Side.
            #               Skills: main primary skill + one skill from either Side.
            # Stacking guard: if a +1 would exceed the per-ability cap (2), fallback to Main's secondary ability.

            # Helper to safely extract ability field keys from Background rows
            def _abil_key(name: str | None) -> str:
                return (name or "").strip().lower()

            if main_bg:
                # Main's primary always applies as +2
                _add_bonus(_abil_key(main_bg.primary_ability), int(main_bg.primary_bonus or 0))

                if side1 or side2:
                    # ---- with Sides ----
                    # One +1 drawn from sides (pick best available)
                    side_pool = [s for s in (side1, side2) if s]
                    chosen = None
                    for s in side_pool:
                        # try primary first, then secondary
                        if _add_one_abil(_abil_key(s.primary_ability)):
                            chosen = s
                            break
                        if _add_one_abil(_abil_key(s.secondary_ability)):
                            chosen = s
                            break
                    if not chosen:
                        # fallback: push main secondary +1 if possible
                        _add_one_abil(_abil_key(main_bg.secondary_ability))

                    # Skills: main primary + one from sides (prefer primary of first viable side)
                    if main_bg.primary_skill:
                        _grant_skill_once(main_bg.primary_skill)

                    picked_side_skill = False
                    for s in side_pool:
                        if s and s.primary_skill and _grant_skill_once(s.primary_skill):
                            picked_side_skill = True
                            break
                        if s and s.secondary_skill and _grant_skill_once(s.secondary_skill):
                            picked_side_skill = True
                            break
                    if not picked_side_skill and main_bg.secondary_skill:
                        # emergency fallback to keep total 2
                        _grant_skill_once(main_bg.secondary_skill)

                else:
                    # ---- Main only ----
                    _add_bonus(_abil_key(main_bg.secondary_ability), int(main_bg.secondary_bonus or 0))
                    if main_bg.primary_skill:
                        _grant_skill_once(main_bg.primary_skill)
                    if main_bg.secondary_skill:
                        _grant_skill_once(main_bg.secondary_skill)



            # Now persist the Character
            character.save()
            def _to_int(v):
                try: return int(v)
                except Exception: return None

            # 1) read the hidden JSON fields your JS fills in

            raw_sc = request.POST.get("racial_subclass_picks") or "{}"   # { "<feature_id>": <subclass_id> }
            raw_ro = request.POST.get("race_option_picks")   or "{}"     # { "<feature_id>": { "option_id": X, "subclass_id": Y? } }
            try: sc_picks = json.loads(raw_sc)
            except Exception: sc_picks = {}
            try: ro_picks = json.loads(raw_ro)
            except Exception: ro_picks = {}

            # 2) determine which RaceFeatures are auto-granted at creation
            feats_qs = (
                character.race.features
                .select_related("subrace", "subclass_group")
                .prefetch_related("subclasses")
            )

            # hide anything that is only granted via a RaceFeatureOption
            granted_ids = set(
                RaceFeatureOption.objects
                    .filter(feature__race=character.race)
                    .values_list("grants_feature_id", flat=True)
            )

            universal = [f for f in feats_qs if not f.subrace_id and f.id not in granted_ids]
            subrace_feats = [
                f for f in feats_qs
                if getattr(character, "subrace_id", None) and f.subrace_id == character.subrace_id and f.id not in granted_ids
            ]

            def _selected_subclass_id_for(feature_id):
                # keys might arrive as "123" or 123
                return _to_int(sc_picks.get(str(feature_id)) or sc_picks.get(feature_id))

            def _upsert_cfeat(racial_feature, subclass_id=None):
                row, _ = CharacterFeature.objects.get_or_create(
                    character=character,
                    racial_feature=racial_feature,
                    defaults={"level": character.level}
                )
                if subclass_id:
                    sub = ClassSubclass.objects.filter(pk=int(subclass_id)).first()
                    if sub and row.subclass_id != sub.id:
                        row.subclass = sub
                        row.save(update_fields=["subclass"])

            # 3) create CharacterFeature rows for the auto-granted features
            for f in (universal + subrace_feats):
                _upsert_cfeat(f, _selected_subclass_id_for(f.id))

            # 4) process any picked RACE OPTIONS that grant an additional feature
            for f_id, payload in (ro_picks or {}).items():
                # payload is {"option_id": <id>, "subclass_id": <id?>} per your JS
                opt_id = _to_int((payload or {}).get("option_id"))
                if not opt_id:
                    continue
                opt = RaceFeatureOption.objects.filter(pk=opt_id).select_related("grants_feature").first()
                if not opt or not opt.grants_feature_id:
                    continue
                sub_id = _to_int((payload or {}).get("subclass_id"))
                _upsert_cfeat(opt.grants_feature, sub_id)
            # ---- Persist skill proficiencies coming from background picks -----------------
            # 1 stacked grant = Trained, 2 stacked grants = Expert (cap at 2, per your rule).
            from .models import ProficiencyLevel, CharacterSkillProficiency

            trained = ProficiencyLevel.objects.filter(name__iexact="Trained").first()
            expert  = ProficiencyLevel.objects.filter(name__iexact="Expert").first()
            tier_by_count = {1: trained, 2: expert}

            for (ctype_id, obj_id), count in skill_counts.items():
                if count <= 0:
                    continue
                tier = tier_by_count.get(min(count, 2))
                if not tier:
                    continue
                CharacterSkillProficiency.objects.update_or_create(
                    character=character,
                    selected_skill_type_id=ctype_id,
                    selected_skill_id=obj_id,
                    defaults={"proficiency": tier},
                )

            # ---- Also accept/merge any frontend-computed rows (keeps your current behavior) ----
            raw = form.cleaned_data.get('computed_skill_proficiencies') or '{}'
            try:
                prof_map = json.loads(raw)
                for full_name, tier_name in prof_map.items():
                    # "Athletics – Climbing" (SubSkill) or plain "Athletics" (Skill)
                    # Try SubSkill first
                    sub = SubSkill.objects.filter(name__iexact=full_name.split(' – ', 1)[-1]).first()
                    if ' – ' in full_name and sub:
                        obj_ct, obj_id = ct_sub, sub.id
                    else:
                        sk = Skill.objects.filter(name__iexact=full_name).first()
                        if not sk:
                            continue
                        obj_ct, obj_id = ct_skill, sk.id

                    prof = ProficiencyLevel.objects.filter(name__iexact=tier_name).first()
                    if not prof:
                        continue

                    # Upgrade if this is higher than what we already saved above
                    existing = CharacterSkillProficiency.objects.filter(
                        character=character,
                        selected_skill_type=obj_ct,
                        selected_skill_id=obj_id
                    ).first()
                    if (not existing) or (prof.bonus > existing.proficiency.bonus):
                        CharacterSkillProficiency.objects.update_or_create(
                            character=character,
                            selected_skill_type=obj_ct,
                            selected_skill_id=obj_id,
                            defaults={"proficiency": prof},
                        )
            except Exception:
                # Don’t fail the create flow; just surface a warning.
                messages.warning(request, "Some skill proficiency data could not be read; backgrounds were applied correctly.")

            return redirect('characters:character_list')

        # Form invalid: explain instead of “resetting”
        messages.error(request, "Please correct the errors below. Your inputs are preserved.")
    else:
        form = CharacterCreationForm()
    # prepare JSON for frontend
    races = []
    for race in Race.objects.prefetch_related('subraces').all():
        # Build a compact, friendly summary label: "Elf — +2 Dex, +1 Int (+1 free)"
        mods = {
            'Strength':     race.strength_bonus,
            'Dexterity':    race.dexterity_bonus,
            'Constitution': race.constitution_bonus,
            'Intelligence': race.intelligence_bonus,
            'Wisdom':       race.wisdom_bonus,
            'Charisma':     race.charisma_bonus,
        }
        mod_parts = [f"+{v} {k[:3]}" for k, v in mods.items() if (v or 0) != 0]
        free_part = f" (+{race.free_points} free)" if (race.free_points or 0) > 0 else ""
        race_label = f"{race.name} — {', '.join(mod_parts) if mod_parts else '+0'}{free_part}"

        races.append({
            'id': race.id,  
            'code': race.code,
            'name': race.name,
            'label': race_label,
            'modifiers': mods,
            'free_points':           race.free_points,
            'max_bonus_per_ability': race.max_bonus_per_ability,
            'subraces': [
                {
                    'id': sub.id, 
                    'code': sub.code,
                    'name': sub.name,
                    'label': (
                        f"{sub.name} — " +
                        ", ".join([f"+{v} {k[:3]}" for k, v in {
                            'Strength':     sub.strength_bonus,
                            'Dexterity':    sub.dexterity_bonus,
                            'Constitution': sub.constitution_bonus,
                            'Intelligence': sub.intelligence_bonus,
                            'Wisdom':       sub.wisdom_bonus,
                            'Charisma':     sub.charisma_bonus,
                        }.items() if (v or 0) != 0]) +
                        (f" (+{sub.free_points} free)" if (sub.free_points or 0) > 0 else "")
                    ),
                    'modifiers': {
                        'Strength':     sub.strength_bonus,
                        'Dexterity':    sub.dexterity_bonus,
                        'Constitution': sub.constitution_bonus,
                        'Intelligence': sub.intelligence_bonus,
                        'Wisdom':       sub.wisdom_bonus,
                        'Charisma':     sub.charisma_bonus,
                    },
                    'free_points':           sub.free_points,
                    'max_bonus_per_ability': sub.max_bonus_per_ability,
                }
                for sub in race.subraces.all()
            ],
        })

    backgrounds = []
    for bg in Background.objects.all():
        backgrounds.append({
            'code': bg.code,
            'name': bg.name,
            'label': _bg_label(bg),  # << shows +ability and profs for the dropdown
            'primary': {
                'ability': bg.get_primary_ability_display(),
                'bonus':   bg.primary_bonus,
                'skill':   _skill_label(bg.primary_skill),
            },
            'secondary': {
                'ability': bg.get_secondary_ability_display(),
                'bonus':   bg.secondary_bonus,
                'skill':   _skill_label(bg.secondary_skill),
            }
        })
    context = {
        'form':             form,
        'races_json':       json.dumps(races,       cls=DjangoJSONEncoder),
        'backgrounds_json': json.dumps(backgrounds, cls=DjangoJSONEncoder),
        # NEW: endpoint the page will call to load features
    }
    return render(request, 'forge/create_character.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import (
    Character, CharacterClassProgress, ClassLevel,
    UniversalLevelFeature, CharacterFeature,
    ClassFeature, ClassSubclass, FeatureOption
)
from .forms import LevelUpForm

# ─────────────────────────────────────────────────────────────────────────────
# Per-item proficiency resolution: highest tier across all your class levels
# ─────────────────────────────────────────────────────────────────────────────
from django.db.models import Q

def _best_tier_obj(tiers):
    """Return the tier with the highest bonus; tiers can be None."""
    tiers = [t for t in tiers if t is not None]
    if not tiers: 
        return None
    return max(tiers, key=lambda t: int(getattr(t, "bonus", 0) or 0))

def _effective_class_prof_for_item(character, prof_type, *, armor_group=None, armor_item_id=None,
                                   weapon_group=None, weapon_item_id=None):
    """
    Look at all of the character's classes and their levels, and return the
    best tier (by .bonus) that applies to this specific item or group.
    Priority: specific item > matching group. If nothing found → Untrained.
    Returns dict: {"tier": <tier or None>, "bonus": int, "name": str, "is_proficient": bool}
    """
    # Collect all rows unlocked by each of your class levels
    rows = []
    for cp in character.class_progress.select_related("character_class").all():
        rows.extend(
            ClassProficiencyProgress.objects.filter(
                character_class=cp.character_class,
                proficiency_type=prof_type,
                at_level__lte=int(cp.levels or 0),
            )
        )

    # Filter for this concrete item (strongest match)
    item_rows = []
    if prof_type == "armor" and armor_item_id:
        item_rows = [r for r in rows if getattr(r, "armor_item_id", None) == armor_item_id]
    if prof_type == "weapon" and weapon_item_id:
        item_rows = [r for r in rows if getattr(r, "weapon_item_id", None) == weapon_item_id]

    if item_rows:
        best = _best_tier_obj([r.tier for r in item_rows])
    else:
        # Fall back to group match
        grp_rows = []
        if prof_type == "armor" and armor_group:
            grp_rows = [r for r in rows if (r.armor_group or "").lower() == str(armor_group).lower()]
        if prof_type == "weapon" and weapon_group:
            grp_rows = [r for r in rows if (r.weapon_group or "").lower() == str(weapon_group).lower()]
        best = _best_tier_obj([r.tier for r in grp_rows])

    # If nothing grants proficiency, treat as Untrained
    name = (best.name if best and getattr(best, "name", None) else "Untrained")
    bonus = int(getattr(best, "bonus", 0) or 0)
    is_prof = (name.strip().lower() != "untrained") and (bonus != 0)

    return {"tier": best, "bonus": bonus, "name": name, "is_proficient": is_prof}

def _armor_group_for(armor_obj):
    # Your Armor model uses .type (you already sort by it elsewhere)
    return getattr(armor_obj, "type", None)

def _weapon_group_for(weapon_obj):
    # Prefer .group if you’ve added it; otherwise fall back to a safe default.
    # (If you don’t have .group yet, see Step 4 below.)
    return getattr(weapon_obj, "group", None) or getattr(weapon_obj, "category", None)

# ────────────────────────────────────────────────────────────────────────────────
# Spell tab helper (extracted from character_detail)
# ────────────────────────────────────────────────────────────────────────────────
# ────────────────────────────────────────────────────────────────────────────────
# Spell tab helper (extracted from character_detail)
# ────────────────────────────────────────────────────────────────────────────────
def _build_spell_tab(request, character, class_progress, can_edit, *, pk):
    """
    Builds the spell tab payloads and handles the two spells_op POST actions.

    Returns:
        (spellcasting_blocks, spell_selection_blocks, post_redirect_or_none)
    """
    # placeholders; will be filled by pasted block
    spellcasting_blocks = []
    spell_selection_blocks = []



    for cp in class_progress:
        owned_tables = (
            ClassFeature.objects
            .filter(kind="spell_table", character_class=cp.character_class)
            .distinct()
        )
        # Build a dict like {"cleric_level": 5, "wizard_level": 2, ...}
        all_class_levels_ctx = {}
        for prog in class_progress:
            # tokenize class name → "cleric", "war_priest", "wizard", etc.
            token = re.sub(r'[^a-z0-9_]', '', (prog.character_class.name or '').strip().lower().replace(' ', '_'))
            if token:
                all_class_levels_ctx[f"{token}_level"] = prog.levels

        for ft in owned_tables:
            row = ft.spell_slot_rows.filter(level=cp.levels).first()

            # safe eval context for formulas stored on ClassFeature
            # --- safe eval helpers / context for spell table formulas ---
            def _abil(score: int) -> int: return (score - 10) // 2

            ctx = {
                # level-in-class variables (cleric_level, wizard_level, etc.)
                # e.g. {'cleric_level': 1, 'war_priest_level': 0, ...}
            }
            for prog in class_progress:
                token = re.sub(r'[^a-z0-9_]', '', (prog.character_class.name or '')
                            .strip().lower().replace(' ', '_'))
                if token:
                    ctx[f"{token}_level"] = int(prog.levels or 0)

            # ability: expose both score and modifier under common aliases
            ctx.update({
                # scores
                    "ceil": math.ceil,
    "round_up": math.ceil,
    "roundup": math.ceil,     # NEW alias
    "ceiling": math.ceil, 
                "strength_score": character.strength, "dexterity_score": character.dexterity,
                "constitution_score": character.constitution, "intelligence_score": character.intelligence,
                "wisdom_score": character.wisdom, "charisma_score": character.charisma,
                # primary short names as **modifiers**
                "strength": _abil(character.strength), "dexterity": _abil(character.dexterity),
                "constitution": _abil(character.constitution), "intelligence": _abil(character.intelligence),
                "wisdom": _abil(character.wisdom), "charisma": _abil(character.charisma),
                # explicit *_mod aliases
                "str_mod": _abil(character.strength), "dex_mod": _abil(character.dexterity),
                "con_mod": _abil(character.constitution), "int_mod": _abil(character.intelligence),
                "wis_mod": _abil(character.wisdom), "cha_mod": _abil(character.charisma),
                # math helpers
                "floor": math.floor, "ceil": math.ceil, "min": min, "max": max,
                "int": int, "round": round, "round_up": math.ceil,
            })

            def _eval(expr: str):
                if not expr:
                    return None
                try:
                    expr = _normalize_formula(expr)       # <<< ADD THIS LINE
                    val = eval(expr, {"__builtins__": {}}, ctx)
                    return int(val)
                except Exception:
                    return None

            # slots by rank (R1..R10)
            slots = []
            if row:
                slots = [row.slot1,row.slot2,row.slot3,row.slot4,row.slot5,
                         row.slot6,row.slot7,row.slot8,row.slot9,row.slot10]
            max_rank = max((i+1 for i, s in enumerate(slots) if (s or 0) > 0), default=0)

            origin_label = (getattr(ft, "get_spell_list_display", lambda: None)() or ft.spell_list or "").strip()
            origin_key   = (ft.spell_list or origin_label or "—").strip().lower()  # normalized key
            origin       = origin_label  # pretty label for UI
       
            cantrips_max  = _eval(getattr(ft, "cantrips_formula", None)) or 0
            known_max     = _eval(getattr(ft, "spells_known_formula", None))  # may be None for prepared casters
            prepared_max  = _eval(getattr(ft, "spells_prepared_formula", None))  # may be None for spontaneous casters
            def _ov_expr(key):
                row = CharacterFieldOverride.objects.filter(character=character, key=key).first()
                return (row.value or "").strip() if row and row.value is not None else None
            expr_can = _ov_expr(f"spellcap_formula:{ft.id}:cantrips")
            expr_kn  = _ov_expr(f"spellcap_formula:{ft.id}:known")
            expr_pr  = _ov_expr(f"spellcap_formula:{ft.id}:prepared")
            # Enforce minimums
            if known_max is not None:
                known_max = max(1, int(known_max))
            if prepared_max is not None:
                prepared_max = max(1, int(prepared_max))

            if expr_can: cantrips_max = _eval(expr_can) or 0
            if expr_kn  is not None: known_max    = _eval(expr_kn)
            if expr_pr  is not None: prepared_max = _eval(expr_pr)
            
            # RE-APPLY minimums after overrides
            if cantrips_max is not None:
                cantrips_max = max(1, int(cantrips_max or 0))
            if known_max is not None:
                known_max = max(1, int(known_max or 0))
            if prepared_max is not None:
                prepared_max = max(1, int(prepared_max or 0))
            def _ov(key):
                row = CharacterFieldOverride.objects.filter(character=character, key=key).first()
                try:
                    return int(row.value) if row and str(row.value).strip() != "" else None
                except Exception:
                    return None

            ov_can = _ov(f"spellcap:{ft.id}:cantrips")
            ov_kn  = _ov(f"spellcap:{ft.id}:known")
            ov_pr  = _ov(f"spellcap:{ft.id}:prepared")

            if ov_can is not None: cantrips_max = ov_can
            if known_max is not None and ov_kn is not None: known_max = ov_kn
            if prepared_max is not None and ov_pr is not None: prepared_max = ov_pr

            # Current counts scoped to this origin/list
            # Current counts scoped to this origin/list
            known_qs_base = character.known_spells.select_related("spell")
            prep_qs_base  = character.prepared_spells.select_related("spell")
            # Spells known by this character regardless of list (avoid dup-learn)
            known_ids_all = set(character.known_spells.values_list("spell_id", flat=True))

            if origin:
                token_re = rf'(^|[,;/\s\(\)]+){re.escape(origin)}([,;/\s\(\)]+|$)'
                known_qs_base = known_qs_base.filter(
                    Q(spell__origin__icontains=origin) |
                    Q(spell__sub_origin__icontains=origin) |
                    Q(spell__origin__iregex=token_re) |
                    Q(spell__sub_origin__iregex=token_re) |
                    Q(origin__icontains=origin) |                     # NEW
                    Q(origin__iregex=token_re)                        # NEW
                )

                # Prepared spells row stores only origin; use contains + token regex
                prep_qs_base  = prep_qs_base.filter(
                    Q(origin__icontains=origin) |
                    Q(origin__iregex=token_re)
                )


            # ----- CLEAR BUCKETS -----
            # Known (aka learned) — split cantrips vs leveled
            known_cantrips_qs = known_qs_base.filter(spell__level=0)
            known_leveled_qs  = known_qs_base.filter(spell__level__gt=0)

            known_cantrips_current = known_cantrips_qs.count()
            known_leveled_current  = known_leveled_qs.count()

            # Prepared – per-rank counts (rank>0 only)
            prepared_per_rank = Counter(prep_qs_base.values_list("rank", flat=True))
            prepared_current  = sum(v for r, v in prepared_per_rank.items() if r and r > 0)

            # Slots remaining per rank (1..max_rank) from this feature’s row
            # NOTE: slots[] is already computed above; slots[i] is for rank i+1
            remaining_by_rank = {
                r: max(0, (slots[r-1] or 0) - int(prepared_per_rank.get(r, 0)))
                for r in range(1, max_rank + 1)
            }
            slots_by_rank = {r: int(slots[r-1] or 0) for r in range(1, max_rank + 1)}

            # ----- AVAILABLE CHOICES -----
            # 0) Base queryset for this origin (define first!)

            origin_code  = origin_key
            # compute slots[] and max_rank as you already do
            max_rank_from_slots = max((i+1 for i, s in enumerate(slots) if (s or 0) > 0), default=0)

            # ensure at least rank 1 is considered if there's a known/prepared entitlement
            has_known_ent = (_eval(getattr(ft, "spells_known_formula", None)) or 0) > 0
            has_prep_ent  = (_eval(getattr(ft, "spells_prepared_formula", None)) or 0) > 0
            max_rank = max(1 if (has_known_ent or has_prep_ent) else 0, max_rank_from_slots)

            # origin filter — only apply if it actually matches anything; else, fall back
            avail_base = Spell.objects.all()
            if origin_label or origin_code:
                token = (origin_label or origin_code).strip()
                token_re = rf'(^|[,;/\s\(\)]+){re.escape(token)}([,;/\s\(\)]+|$)'
                filtered = avail_base.filter(
                    Q(origin__icontains=token) | Q(sub_origin__icontains=token) |
                    Q(origin__iregex=token_re) | Q(sub_origin__iregex=token_re)
                )
                avail_base = filtered if filtered.exists() else avail_base  # <- don’t erase list if dirty data


            # 1) Columns to return to the UI  (include id; fix the 'range','target' comma)
            cols = [
                "id", "name", "level", "classification", "effect", "upcast_effect",
                "saving_throw", "casting_time", "duration", "components",
                "range", "target", "origin", "sub_origin", "tags", "last_synced",
            ]

            # 2) Cantrips to learn (not yet known)
            cantrip_choices = list(
                avail_base.filter(level=0)
                        .exclude(pk__in=known_ids_all)
                        .order_by("name")
                        .values(*cols)
            )

            # 3) Leveled spells to learn, grouped by rank
            spell_choices_by_rank = {}
            for r in range(1, max_rank + 1):
                spell_choices_by_rank[r] = list(
                    avail_base.filter(level=r)
                            .exclude(pk__in=known_ids_all)
                            .order_by("name")
                            .values(*cols)
                )



            known_leveled_rows = list(
                known_leveled_qs.order_by("spell__level", "spell__name")
                                .values("spell_id", "spell__name", "spell__level")
            )
            prepare_choices_by_rank = {r: [] for r in range(1, max_rank + 1)}
            for rec in known_leveled_rows:
                r = int(rec["spell__level"])
                if 1 <= r <= max_rank:
                    prepare_choices_by_rank[r].append(
                        {"id": rec["spell_id"], "name": rec["spell__name"], "rank": r}
                    )
            spellcasting_blocks.append({
                "klass": cp.character_class,
                "list": (origin_label or origin or "").strip(),
                "slots": [int(slots[i] or 0) for i in range(max_rank)],
                "cantrips": int(cantrips_max or 0),
                "known": (int(known_max) if known_max is not None else None),
                "prepared": (int(prepared_max) if prepared_max is not None else None),
            })
            # block used by current Spellcasting tab (kept)
            def _spell_rows_from_qs(qs, add_origin=None):
                rows = []
                for s in qs.select_related("spell").order_by("spell__level", "spell__name"):
                    sp = s.spell
                    rows.append({
                        "id": sp.id,
                        "known_id": getattr(s, "id", None),
                        "prepared_id": getattr(s, "id", None),
                        "name": sp.name,
                        "origin": add_origin if add_origin is not None else (sp.origin or ""),
                        "sub_origin": sp.sub_origin or "",
                        "level": sp.level,                             # ← NEW
                        "rank": getattr(s, "rank", sp.level),          # keep for prepare tables
                        "classification": sp.classification or "",
                        "saving_throw": sp.saving_throw or "",
                        "casting_time": sp.casting_time or "",
                        "duration": sp.duration or "",
                        "components": sp.components or "",
                        "range": sp.range or "",
                        "target": sp.target or "",
                        "tags": sp.tags or "",
                        "last_synced": sp.last_synced,
                        "effect": sp.effect or "",
                        "upcast_effect": sp.upcast_effect or "",
                    })
                return rows




            def _spell_rows_from_values(values_list, add_origin=None):
                # values_list is what you already have in cantrip_choices / spell_choices_by_rank
                out = []
                for v in values_list:
                    out.append({
                        "id": v["id"],
                        "name": v["name"],
                        "origin": add_origin if add_origin is not None else (v.get("origin") or ""),
                        "sub_origin": v.get("sub_origin") or "",
                        "level": v["level"],   
                        "rank": v["level"],
                        "classification": v.get("classification") or "",
                        "saving_throw": v.get("saving_throw") or "",
                        "casting_time": v.get("casting_time") or "",
                        "duration": v.get("duration") or "",
                        "components": v.get("components") or "",
                        "range": v.get("range") or "",
                        "target": v.get("target") or "",
                        "tags": v.get("tags") or "",
                        "last_synced": v.get("last_synced"),
                        # details-only
                        "effect": v.get("effect") or "",
                        "upcast_effect": v.get("upcast_effect") or "",
                    })
                return out

            # 1) Prepared spells (by rank)
            prepared_rows_by_rank = {r: [] for r in range(1, max_rank + 1)}
            if max_rank > 0:
                prep_full = prep_qs_base.select_related("spell").order_by("rank", "spell__name")
                for r in range(1, max_rank + 1):
                    prepared_rows_by_rank[r] = _spell_rows_from_qs(
                        prep_full.filter(rank=r), add_origin=origin_key
                    )

            # 2) Learned cantrips (rank 0, from known)
            learned_cantrips_rows = _spell_rows_from_qs(known_cantrips_qs, add_origin=origin_key)

            # 3) From KNOWN (rank > 0) → available to PREPARE (exclude ones already prepared)
            prepared_ids = set(prep_qs_base.values_list("spell_id", flat=True))
            known_for_prepare_by_rank = {r: [] for r in range(1, max_rank + 1)}
            if max_rank > 0:
                known_full = known_leveled_qs.select_related("spell").order_by("spell__level", "spell__name")
                for r in range(1, max_rank + 1):
                    subset = known_full.filter(spell__level=r).exclude(spell_id__in=prepared_ids)
                    known_for_prepare_by_rank[r] = _spell_rows_from_qs(subset, add_origin=origin_key)


            # 4) From full LIST → available to KNOW (rank > 0)  (already computed in spell_choices_by_rank)
            learn_spells_by_rank = {
                r: _spell_rows_from_values(spell_choices_by_rank.get(r, []), add_origin=(origin or ""))
                for r in range(1, max_rank + 1)
            }

            # 5) From full LIST → available to LEARN (cantrips)
            learn_cantrip_rows = _spell_rows_from_values(cantrip_choices, add_origin=origin_key)
            has_any_override = CharacterFieldOverride.objects.filter(
                character=character,
                key__in=[
                    f"spellcap_formula:{ft.id}:cantrips",
                    f"spellcap_formula:{ft.id}:known",
                    f"spellcap_formula:{ft.id}:prepared",
                    f"spellcap:{ft.id}:cantrips",
                    f"spellcap:{ft.id}:known",
                    f"spellcap:{ft.id}:prepared",
                ]
            ).exists()
            spell_selection_blocks.append({
            "cantrips_formula": getattr(ft, "cantrips_formula", "") or "",
              "spells_known_formula": getattr(ft, "spells_known_formula", "") or "",
               "spells_prepared_formula": getattr(ft, "spells_prepared_formula", "") or "",
                # ── unchanged context you already had ───────────────────────────────────
                "feature_id": ft.id,
                "has_any_override": has_any_override,
                "class_name": cp.character_class.name,
                "origin": origin_key,
                "origin_code": (ft.spell_list or "").lower(),
                "max_rank": max_rank,
                "cantrips_max": int(cantrips_max or 0),
                "known_max": (int(known_max) if known_max is not None else None),
                "prepared_max": (int(prepared_max) if prepared_max is not None else None),
                "known_cantrips_current": known_cantrips_current,
                "known_leveled_current":  known_leveled_current,
                "prepared_current":       prepared_current,
                "needs_cantrips": max(0, int(cantrips_max) - known_cantrips_current),
                "needs_known":    (max(0, int(known_max) - known_leveled_current) if known_max is not None else None),

                "needs_prepared": max(0, int(prepared_max or 0) - prepared_current) if prepared_max is not None else None,
                "prepared_remaining_by_rank": remaining_by_rank,
                "slots_by_rank": slots_by_rank,

                # ── NEW: 5 sections for the Spellcasting tab ───────────────────────────
                # 1
                "prepared_rows_by_rank": prepared_rows_by_rank,
                # 2
                "learned_cantrips_rows": learned_cantrips_rows,
                # 3
                "known_for_prepare_by_rank": known_for_prepare_by_rank,
                # 4
                "learn_spells_by_rank": learn_spells_by_rank,
                # 5
                "learn_cantrip_rows": learn_cantrip_rows,
            })


    if request.method == "POST" and request.POST.get("spells_op") == "adjust_formulas" and can_edit:
        fid = int(request.POST.get("feature_id") or 0)
        note = (request.POST.get("note") or "").strip()
        if not note:
            messages.error(request, "Reason is required.")
            return (spellcasting_blocks, spell_selection_blocks, redirect('characters:character_detail', pk=pk))


        def _save_expr(kind, form_key):
            expr = (request.POST.get(form_key) or "").strip()
            key = f"spellcap_formula:{fid}:{kind}"
            # empty -> clear override
            if expr == "":
                CharacterFieldOverride.objects.filter(character=character, key=key).delete()
            else:
                CharacterFieldOverride.objects.update_or_create(
                    character=character, key=key, defaults={"value": expr}
                )
            CharacterFieldNote.objects.update_or_create(
                character=character, key=key, defaults={"note": note}
            )

        _save_expr("cantrips", "f_cantrips")
        _save_expr("known",    "f_known")
        _save_expr("prepared", "f_prepared")

        return redirect('characters:character_detail', pk=pk)

    if request.method == "POST" and request.POST.get("spells_op") == "reset_caps" and can_edit:
        fid = int(request.POST.get("feature_id") or 0)
        CharacterFieldOverride.objects.filter(
            character=character,
            key__regex=rf'^spellcap(_formula)?:{fid}:(cantrips|known|prepared)$'
        ).delete()
        CharacterFieldNote.objects.filter(
            character=character,
            key__regex=rf'^spellcap(_formula)?:{fid}:(cantrips|known|prepared)$'
        ).delete()
        messages.success(request, "Personal caps/formulas reset to defaults.")
        return (spellcasting_blocks, spell_selection_blocks, redirect('characters:character_detail', pk=pk))


    # If none of the POST branches early-returned, fall through normally:
    return (spellcasting_blocks, spell_selection_blocks, None)


@login_required
def character_detail(request, pk):
    # ── 1) Load character & basic sheet context ─────────────────────────────
    character = get_object_or_404(Character, pk=pk)

    is_gm_for_campaign = False
    if character.campaign_id:
        is_gm_for_campaign = CampaignMembership.objects.filter(
            campaign=character.campaign, user=request.user, role="gm"
        ).exists()

    if not (request.user.id == character.user_id or is_gm_for_campaign):
        return HttpResponseForbidden("You don’t have permission to view this character.")

    can_edit = (request.user.id == character.user_id) or is_gm_for_campaign    
    if request.method == "POST" and "level_up_submit" in request.POST:
        return character_level_up(request, pk)
    # LOR skill progression constants
    LOR_TIER_ORDER     = ["Untrained","Trained","Expert","Master","Legendary"]
    LOR_UPGRADE_COST   = {"Untrained":1, "Trained":2, "Expert":3, "Master":5}   # → next tier
    LOR_MIN_LEVEL_FOR  = {"Trained":0, "Expert":3, "Master":7, "Legendary":14}  # first level you may *reach* that tier

    def _tier_name(pl):
        return (pl.name if pl else "Untrained").title()

    def _next_tier_name(current_name):
        try:
            i = LOR_TIER_ORDER.index(current_name.title())
            return LOR_TIER_ORDER[i+1] if i+1 < len(LOR_TIER_ORDER) else None
        except ValueError:
            return "Trained"  # safety

    def _upgrade_cost(current_name):
        return LOR_UPGRADE_COST.get(current_name.title(), 1)

    def _min_level_to_reach(tier_name):
        return LOR_MIN_LEVEL_FOR.get(tier_name.title(), 99)

    # Switchable refund behavior: "step"=just the last step; "full"=all invested in current tier path
    RETRAIN_REFUND_MODE = "step"

    ability_map = {
        'Strength':     character.strength,
        'Dexterity':    character.dexterity,
        'Constitution': character.constitution,
        'Intelligence': character.intelligence,
        'Wisdom':       character.wisdom,
        'Charisma':     character.charisma,
    }
    racial_feature_rows = (
    CharacterFeature.objects
        .filter(character=character, racial_feature__isnull=False)
        .select_related("racial_feature", "subclass")
        .order_by("level", "racial_feature__name")
)
    abilities = []
    for label, score in ability_map.items():
        m = _abil_mod(score)
        abilities.append({
            "label": label,           # "Strength"
            "key": label.lower(),     # "strength" (used by your editable helper)
            "score": score,           # 15
            "mod": m,                 # 2
            "mod_str": f"{'+' if m >= 0 else ''}{m}",
        })
    skill_proficiencies = list(character.skill_proficiencies.all())
    skill_proficiencies.sort(key=lambda sp: (getattr(sp.selected_skill, "name", "") or "").lower())

    class_progress  = character.class_progress.select_related('character_class')
    racial_features = character.race.features.all() if character.race else []
    universal_feats = UniversalLevelFeature.objects.filter(level=character.level)
    total_level     = character.level
    subrace_name    = (character.subrace.name 
                       if getattr(character, 'subrace', None) else None)

    # ── 2) Determine which class we’re leveling in / previewing ───────────
    next_level = total_level + 1
    first_prog = class_progress.first()
    default_cls = first_prog.character_class if first_prog else CharacterClass.objects.order_by("name").first()
    if not default_cls:
        return render(request, 'forge/character_detail.html', {"error": "No classes defined."})


    # If a GET param “base_class” is present, use that; otherwise use default
    selected_pk = (request.POST.get('base_class') or request.GET.get('base_class'))
    try:
        preview_cls = CharacterClass.objects.get(pk=int(selected_pk)) if (selected_pk and str(selected_pk).isdigit()) else default_cls
    except CharacterClass.DoesNotExist:
        preview_cls = default_cls


    subclass_groups = list(
    preview_cls.subclass_groups
        .order_by('name')
        .prefetch_related('subclasses', 'tier_levels')
)
    cls_level_after = _class_level_after_pick(character, preview_cls)
    cls_level_after_post = cls_level_after
    show_starting_skill_picker = (cls_level_after == 1)  # only at first level in this class

    starting_skill_choices = {"skills": [], "subskills": []}
    starting_skill_max = 0  # <-- NEW




    def _starting_skills_cap_for(cls_obj):
        expr = (getattr(cls_obj, "starting_skills_formula", "") or "").strip()
        if not expr:
            return 0

        def _abil(score: int) -> int:
            return (score - 10) // 2

        # IMPORTANT: short names -> MODIFIERS
        ctx = {
            # modifiers (primary names)
            "strength": _abil(character.strength), "dexterity": _abil(character.dexterity),
            "constitution": _abil(character.constitution), "intelligence": _abil(character.intelligence),
            "wisdom": _abil(character.wisdom), "charisma": _abil(character.charisma),

            # explicit *_mod aliases (same values as above)
            "str_mod": _abil(character.strength), "dex_mod": _abil(character.dexterity),
            "con_mod": _abil(character.constitution), "int_mod": _abil(character.intelligence),
            "wis_mod": _abil(character.wisdom), "cha_mod": _abil(character.charisma),

            # scores (only if you want them available explicitly)
            "strength_score": character.strength, "dexterity_score": character.dexterity,
            "constitution_score": character.constitution, "intelligence_score": character.intelligence,
            "wisdom_score": character.wisdom, "charisma_score": character.charisma,

            # math/helpers
            "floor": math.floor, "ceil": math.ceil, "min": min, "max": max,
            "int": int, "round": round,
        }

        # <class>_level tokens (wizard_level, fighter_level, ...)
        for prog in character.class_progress.select_related('character_class'):
            token = re.sub(r'[^a-z0-9_]', '', (prog.character_class.name or '')
                        .strip().lower().replace(' ', '_'))
            if token:
                ctx[f"{token}_level"] = int(prog.levels or 0)

        try:
            val = eval(_normalize_formula(expr), {"__builtins__": {}}, ctx)
            return max(0, int(val))
        except Exception:
            return 0

    if show_starting_skill_picker:
        # compute cap for the PREVIEWED class (GET)
        starting_skill_max = _starting_skills_cap_for(preview_cls)

        ct_skill = ContentType.objects.get_for_model(Skill)
        ct_sub   = ContentType.objects.get_for_model(SubSkill)
        already = set(
            character.skill_proficiencies.values_list("selected_skill_type_id", "selected_skill_id")
        )

        # skills with no subskills, non-advanced
        for sk in (Skill.objects
                .filter(subskills__isnull=True, is_advanced=False)
                .order_by("name")):
            if (ct_skill.id, sk.id) not in already:
                starting_skill_choices["skills"].append({"id": sk.id, "label": sk.name})

        # all subskills of non-advanced skills
        for sub in (SubSkill.objects
                    .filter(skill__is_advanced=False)
                    .select_related("skill")
                    .order_by("skill__name", "name")):
            if (ct_sub.id, sub.id) not in already:
                starting_skill_choices["subskills"].append({
                    "id": sub.id,
                    "label": f"{sub.skill.name} – {sub.name}",
                })

    # keep the preview version for GET/UI preview
    try:
        cl_preview = (
            ClassLevel.objects
            .prefetch_related(
                'features__subclasses',
                'features__subclass_group',
                'features__options__grants_feature',
            )
            .get(character_class=preview_cls, level=cls_level_after)
        )
        base_feats_preview = list(cl_preview.features.all())
    except ClassLevel.DoesNotExist:
        base_feats_preview = []

    # decide which set drives validation (POST: posted class; GET: preview)
    data = request.POST if request.method == 'POST' else request.GET
    if request.method == 'POST':
        posted_cls_id = data.get('base_class')
        try:
            posted_cls = CharacterClass.objects.get(pk=int(posted_cls_id))
        except (TypeError, ValueError, CharacterClass.DoesNotExist):
            posted_cls = preview_cls
        cls_level_for_validate = _class_level_after_pick(character, posted_cls)

        try:
            cl_validate = (
                ClassLevel.objects
                .prefetch_related(
                    'features__subclasses',
                    'features__subclass_group',
                    'features__options__grants_feature',
                )
                .get(character_class=posted_cls, level=cls_level_for_validate)
            )
            base_feats_validate = list(cl_validate.features.all())
        except ClassLevel.DoesNotExist:
            base_feats_validate = []

        base_feats = base_feats_validate
    else:
        cls_level_for_validate = _class_level_after_pick(character, preview_cls)
        base_feats = base_feats_preview

    # only real ClassFeature instances go here

    _grants_class_feat_at = any(
        isinstance(f, ClassFeature) and (
            # explicit scopes
            (getattr(f, "scope", "") in ("class_feat_pick", "class_feat_choice"))
            # name contains "class feat" like "Druid Class Feat"
            or ("class feat" in (f.name or "").strip().lower())
            # code contains class_feat-ish marker
            or ("class_feat" in ((getattr(f, "code", "") or "").strip().lower()))
            # kind variants you use in data
            or ((getattr(f, "kind", "") or "").strip().lower()
                in ("class_feat_pick", "class_feat_choice", "grant_class_feat"))
        )
        for f in base_feats
    )



    # --- spellcasting entitlements + selections ---
    (
        spellcasting_blocks,
        spell_selection_blocks,
        _spell_redirect
    ) = _build_spell_tab(request, character, class_progress, can_edit, pk=pk)

    if _spell_redirect:
        return _spell_redirect

    def _formula_override(key: str):
        row = CharacterFieldOverride.objects.filter(character=character, key=f"formula:{key}").first()
        return (row.value or "").strip() if row else None

    def _final_override(key: str):
        row = CharacterFieldOverride.objects.filter(character=character, key=f"final:{key}").first()
        try:
            return int(row.value) if row and str(row.value).strip() != "" else None
        except Exception:
            return None



    if request.method == "POST" and request.POST.get("spells_op") == "reset_caps" and can_edit:
        fid = int(request.POST.get("feature_id") or 0)
        CharacterFieldOverride.objects.filter(
            character=character,
            key__regex=rf'^spellcap(_formula)?:{fid}:(cantrips|known|prepared)$'
        ).delete()
        CharacterFieldNote.objects.filter(
            character=character,
            key__regex=rf'^spellcap(_formula)?:{fid}:(cantrips|known|prepared)$'
        ).delete()
        messages.success(request, "Personal caps/formulas reset to defaults.")
        return redirect('characters:character_detail', pk=pk)


    # which feature‐objects are auto‐granted

    remove_form = RemoveItemsForm(request.POST or None, character=character) if can_edit else None

    if request.method == "POST" and "remove_items_submit" in request.POST and can_edit:
        if remove_form.is_valid():
            reason = remove_form.cleaned_data["reason"]

            # delete selected feats
            for cf in remove_form.cleaned_data["remove_feats"]:
                # log
                CharacterManualGrant.objects.create(
                    character=character,
                    content_type=ContentType.objects.get_for_model(cf.feat.__class__),
                    object_id=cf.feat.pk,
                    reason=f"Removed feat (L{cf.level}): {cf.feat.name}. Reason: {reason}"
                )
                cf.delete()

            # delete selected features
            for cfeat in remove_form.cleaned_data["remove_features"]:
                label = cfeat.feature.name if cfeat.feature else (cfeat.option.label if cfeat.option else "—")
                CharacterManualGrant.objects.create(
                    character=character,
                    content_type=ContentType.objects.get_for_model((cfeat.feature or cfeat).__class__),
                    object_id=(cfeat.feature.pk if cfeat.feature else cfeat.pk),
                    reason=f"Removed feature (L{cfeat.level}): {label}. Reason: {reason}"
                )
                cfeat.delete()

            return redirect('characters:character_detail', pk=pk)    
    auto_feats = [
        f for f in base_feats
        if isinstance(f, ClassFeature) and (
            f.scope == 'class_feat' or getattr(f, "kind", "") == "spell_table"
        )
    ]

    for f in auto_feats:
        if getattr(f, "kind", "") == "spell_table":
            row = f.spell_slot_rows.filter(level=cls_level_after).first()
            # attach so the template can render it
            f.spell_row_next = row
    # universal‐level trigger (only informs the form)
    uni = UniversalLevelFeature.objects.filter(level=next_level).first()

    # only real ClassFeature instances go here
    to_choose = base_feats.copy()



    # ── 3) PROFICIENCY TABLE FOR preview_cls ────────────────────────────────
    profs = list(
        preview_cls.prof_progress
                   .select_related('tier')
                   .order_by('proficiency_type','tier__bonus')
    )
    tiers      = sorted({p.tier for p in profs}, key=lambda t: t.bonus)
    tier_names = [t.name for t in tiers]
    matrix = {p.get_proficiency_type_display(): [None]*len(tiers) for p in profs}
    for p in profs:
        matrix[p.get_proficiency_type_display()][tier_names.index(p.tier.name)] = p.at_level
    proficiency_rows = [
        {'type': pt, 'levels': matrix[pt]}
        for pt in matrix
    ]

    # ── 4) BIND & HANDLE LEVEL‐UP (POST) ───────────────────────────────────
    # ── 4) BIND & HANDLE LEVEL‐UP ─────────────────────────────────────────
    edit_form = CharacterCreationForm(request.POST or None, instance=character) if can_edit else None
    # views.py inside character_detail(), POST branch handling `edit_character_submit`
    details_form = (
        CharacterDetailsForm(request.POST or None, instance=character)
        if can_edit else CharacterDetailsForm(instance=character)
    )
 
    # -- Details editor (requires a reason per changed field) ----------------------
    if request.method == "POST" and "update_details_submit" in request.POST and can_edit:
        details_form = CharacterDetailsForm(request.POST, instance=character)
        if details_form.is_valid():
            changed = details_form.changed_data
            missing = []
            for f in changed:
                if not (request.POST.get(f"note__{f}") or "").strip():
                    missing.append(f)

            if missing:
                for f in missing:
                    details_form.add_error(None, f'Please provide a reason for changing “{f}”.')
            else:
                details_form.save()
                for f in changed:
                    CharacterFieldNote.objects.update_or_create(
                        character=character,
                        key=f,
                        defaults={"note": (request.POST.get(f"note__{f}") or "").strip()}
                    )
                return redirect('characters:character_detail', pk=pk)
        # fall through to render with errors


        edit_form = CharacterCreationForm(request.POST, instance=character)
        if edit_form.is_valid():
            changed = edit_form.changed_data  # fields whose values actually changed
            missing = []
            for field in changed:
                if not (request.POST.get(f"note__{field}") or "").strip():
                    missing.append(field)

            if missing:
                for f in missing:
                    edit_form.add_error(None, f"Please provide a reason for changing “{f}”.")
            else:
                character = edit_form.save()
                # persist/update notes
                for key, note in request.POST.items():
                    if key.startswith("note__"):
                        k = key[6:]
                        note = note.strip()
                        if note:
                            CharacterFieldNote.objects.update_or_create(
                                character=character, key=k, defaults={"note": note}
                            )
                        else:
                            CharacterFieldNote.objects.filter(character=character, key=k).delete()
                return redirect('characters:character_detail', pk=pk)
    # --- CORE STATS (HP / Temp HP / Max HP) quick edit ---
    if request.method == "POST" and "save_core_stats_submit" in request.POST and can_edit:
        def _save_num(key):
            raw = (request.POST.get(key) or "").strip()
            if raw == "":
                return
            try:
                val = int(raw)
            except (TypeError, ValueError):
                messages.error(request, f"{key} must be a number.")
                raise
            CharacterFieldOverride.objects.update_or_create(
                character=character, key=key, defaults={"value": str(val)}
            )
            note = (request.POST.get(f"note__{key}") or "").strip()
            if note:
                CharacterFieldNote.objects.update_or_create(
                    character=character, key=key, defaults={"note": note}
                )
        try:
            _save_num("HP")
            _save_num("temp_HP")
            _save_num("hp_max")
        except Exception:
            return redirect('characters:character_detail', pk=pk)
        return redirect('characters:character_detail', pk=pk)



    # --- GENERIC OVERRIDE SAVE (Formula / Final) from the ✎ modal ---------------
    if request.method == "POST" and request.POST.get("override_submit") == "1" and can_edit:
        # Expected fields from your ✎ modal form
        key     = (request.POST.get("override_key") or "").strip()            # e.g. "skill:sk_12:1"
        formula = (request.POST.get("override_formula") or "").strip()        # free-text
        final_s = (request.POST.get("override_final") or "").strip()          # number or ""
        reason  = (request.POST.get("override_reason") or "").strip()

        if not key:
            messages.error(request, "Missing override key.")
            return redirect('characters:character_detail', pk=pk)
        if not reason:
            messages.error(request, "Reason is required.")
            return redirect('characters:character_detail', pk=pk)

        # Save/Clear FORMULA override (string)
        if formula == "":
            CharacterFieldOverride.objects.filter(character=character, key=f"formula:{key}").delete()
            CharacterFieldNote.objects.filter(character=character, key=f"formula:{key}").delete()
        else:
            CharacterFieldOverride.objects.update_or_create(
                character=character, key=f"formula:{key}", defaults={"value": formula}
            )
            CharacterFieldNote.objects.update_or_create(
                character=character, key=f"formula:{key}", defaults={"note": reason}
            )

        # Save/Clear FINAL override (int)
        if final_s == "":
            CharacterFieldOverride.objects.filter(character=character, key=f"final:{key}").delete()
            CharacterFieldNote.objects.filter(character=character, key=f"final:{key}").delete()
        else:
            try:
                final_i = int(final_s)
            except ValueError:
                messages.error(request, "Final value must be a number.")
                return redirect('characters:character_detail', pk=pk)
            CharacterFieldOverride.objects.update_or_create(
                character=character, key=f"final:{key}", defaults={"value": str(final_i)}
            )
            CharacterFieldNote.objects.update_or_create(
                character=character, key=f"final:{key}", defaults={"note": reason}
            )

        messages.success(request, "Override saved.")
        return redirect('characters:character_detail', pk=pk)
    # --- SKILLS: additive adjustments with reasons (multi-entry) -------------------
    if request.method == "POST" and can_edit and request.POST.get("skills_op"):
        op = (request.POST.get("skills_op") or "").strip()
        # add_delta: create a new unique override row "skill_delta:<id_key>:<uid>"
        if op == "add_delta":
            id_key = (request.POST.get("id_key") or "").strip()         # e.g. "sk_12" or "sub_45"
            delta_s = (request.POST.get("delta") or "").strip()          # signed int: "+2" or "-1" or "2"
            note    = (request.POST.get("note") or "").strip()
            if not id_key:
                messages.error(request, "Missing skill row key.")
                return redirect('characters:character_detail', pk=pk)
            if not note:
                messages.error(request, "Reason is required.")
                return redirect('characters:character_detail', pk=pk)
            try:
                # allow leading +/-
                delta = int(eval(delta_s, {"__builtins__": {}}, {}))
            except Exception:
                messages.error(request, "Adjustment must be a whole number (e.g., -1, 0, +2).")
                return redirect('characters:character_detail', pk=pk)
            uid = uuid.uuid4().hex[:8]
            k = f"skill_delta:{id_key}:{uid}"
            CharacterFieldOverride.objects.update_or_create(
                character=character, key=k, defaults={"value": str(delta)}
            )
            CharacterFieldNote.objects.update_or_create(
                character=character, key=k, defaults={"note": note}
            )
            messages.success(request, "Adjustment added.")
            return redirect('characters:character_detail', pk=pk)

        # remove_delta: remove a specific past change
        if op == "remove_delta":
            mod_key = (request.POST.get("mod_key") or "").strip()        # must be full key "skill_delta:sk_12:abcd1234"
            if not mod_key.startswith("skill_delta:"):
                messages.error(request, "Invalid adjustment key.")
                return redirect('characters:character_detail', pk=pk)
            CharacterFieldOverride.objects.filter(character=character, key=mod_key).delete()
            CharacterFieldNote.objects.filter(character=character, key=mod_key).delete()
            messages.success(request, "Adjustment removed.")
            return redirect('characters:character_detail', pk=pk)

        # clear_deltas: remove all changes on a given row at once
        if op == "clear_deltas":
            id_key = (request.POST.get("id_key") or "").strip()
            CharacterFieldOverride.objects.filter(
                character=character, key__startswith=f"skill_delta:{id_key}:"
            ).delete()
            CharacterFieldNote.objects.filter(
                character=character, key__startswith=f"skill_delta:{id_key}:"
            ).delete()
            messages.success(request, "All adjustments cleared for this skill.")
            return redirect('characters:character_detail', pk=pk)


    manual_form = ManualGrantForm(request.POST or None) if can_edit else None
    # NEW: independent handler for “Manually Add Item”
    # Make selects show nice labels instead of "object (id)"
    if manual_form:
        if "feat" in manual_form.fields:
            manual_form.fields["feat"].label_from_instance = lambda obj: getattr(obj, "name", str(obj))
            manual_form.fields["feat"].queryset = manual_form.fields["feat"].queryset.order_by("name")

        if "class_feature" in manual_form.fields:
            def _cf_label(obj):
                base = getattr(obj, "name", str(obj))
                cls  = getattr(getattr(obj, "character_class", None), "name", "")
                return f"{base} — {cls}" if cls else base
            manual_form.fields["class_feature"].label_from_instance = _cf_label
            manual_form.fields["class_feature"].queryset = manual_form.fields["class_feature"].queryset.order_by("name")

        if "racial_feature" in manual_form.fields:
            manual_form.fields["racial_feature"].label_from_instance = lambda obj: getattr(obj, "name", str(obj))
            manual_form.fields["racial_feature"].queryset = manual_form.fields["racial_feature"].queryset.order_by("name")

    if request.method == 'POST' and 'manual_add_submit' in request.POST and can_edit:
        if manual_form and manual_form.is_valid():
            kind   = manual_form.cleaned_data['kind']
            reason = manual_form.cleaned_data['reason']

            if kind == "feat":
                obj = manual_form.cleaned_data['feat']
            elif kind == "class_feature":
                obj = manual_form.cleaned_data['class_feature']
            else:
                obj = manual_form.cleaned_data['racial_feature']

            ct = ContentType.objects.get_for_model(obj.__class__)
            CharacterManualGrant.objects.create(
                character=character, content_type=ct, object_id=obj.pk, reason=reason
            )

            # Mirror into normal tables at current level
            if kind == "feat":
                CharacterFeat.objects.get_or_create(
                    character=character, feat=obj, defaults={"level": character.level}
                )
            elif kind == "class_feature":
                CharacterFeature.objects.get_or_create(
                    character=character, feature=obj, level=character.level
                )
            elif kind == "racial_feature":
                CharacterFeature.objects.get_or_create(
                    character=character, racial_feature=obj, level=character.level
                )

            return redirect('characters:character_detail', pk=pk)
        # invalid form -> fall through to render with errors


    level_form = LevelUpForm(
        data or None,
        character=character,
        to_choose=to_choose,
        uni=uni,
        preview_cls=preview_cls,             # keep for UI preview
        grants_class_feat=_grants_class_feat_at
    )

    # Add the field *only* when the validated class/level needs it
    if _grants_class_feat_at and "class_feat_pick" not in level_form.fields:
        level_form.fields["class_feat_pick"] = forms.ModelChoiceField(
            queryset=ClassFeat.objects.all(),  # filled by the filter block below
            required=True,
            label="Class Feat"
        )

    # ── NEW: Skill Feat picker(s) when the selected class grants them at this level ──
    # Determine the target class/level we are validating against
    target_cls = posted_cls if request.method == 'POST' else preview_cls
    skill_grant = (
        ClassSkillFeatGrant.objects
        .filter(character_class=target_cls, at_level=cls_level_for_validate)
        .first()
    )

    if skill_grant and "skill_feat_pick" not in level_form.fields:
        picks = int(skill_grant.num_picks or 0)
        base_qs = ClassFeat.objects.all()  # will be filtered to feat_type='Skill' below
        if picks <= 1:
            level_form.fields["skill_feat_pick"] = forms.ModelChoiceField(
                queryset=base_qs,
                required=(picks > 0),
                label="Skill Feat",
                help_text=(None if picks > 0 else "No skill-feat pick at this level.")
            )
        else:
            level_form.fields["skill_feat_pick"] = forms.ModelMultipleChoiceField(
                queryset=base_qs,
                required=(picks > 0),
                label=f"Pick {picks} Skill Feat(s)",
                widget=forms.CheckboxSelectMultiple
            )



    # INIT HERE so we can append immediately below
    feature_fields = []

    gain_sub_feat_triggers = [
        f for f in to_choose
        if isinstance(f, ClassFeature) and f.scope == 'gain_subclass_feat'
    ]

    def _active_subclass_for_group(character, grp, level_form=None, base_feats=None):
        """
        Returns the chosen Subclass for `grp` using (in order):
        1) the POSTed choice this request (if present),
        2) the last saved 'subclass_choice' CharacterFeature,
        3) the last saved 'subclass_feat' (infers subclass),
        4) an explicit override 'subclass_choice:<grp.id>' if you use that,
        else None.
        """
        # 0) if this request posts a subclass choice field, use it
        if level_form is not None and getattr(level_form, "is_bound", False):
            base_feats = list(base_feats or [])
            sc_choices = [
                f for f in base_feats
                if isinstance(f, ClassFeature)
                and getattr(f, "scope", "") == "subclass_choice"
                and getattr(f, "subclass_group_id", None) == grp.id
            ]
            for f in sc_choices:
                key = f"feat_{f.pk}_subclass"
                raw = (level_form.data.get(key) or "").strip()
                if raw.isdigit():
                    try:
                        return grp.subclasses.get(pk=int(raw))
                    except grp.subclasses.model.DoesNotExist:
                        pass

        # 1) last explicitly saved subclass choice
        row = (CharacterFeature.objects
            .filter(character=character,
                    feature__scope="subclass_choice",
                    feature__subclass_group=grp)
            .exclude(subclass__isnull=True)
            .order_by("-level", "-id")
            .first())
        if row and row.subclass_id:
            return row.subclass

        # 2) infer from owned subclass features
        row = (CharacterFeature.objects
            .filter(character=character,
                    feature__scope="subclass_feat",
                    feature__subclass_group=grp)
            .exclude(subclass__isnull=True)
            .order_by("-level", "-id")
            .first())
        if row and row.subclass_id:
            return row.subclass

        # 3) optional manual override
        ov = CharacterFieldOverride.objects.filter(character=character, key=f"subclass_choice:{grp.id}").first()
        if ov and str(ov.value).strip().isdigit():
            try:
                return grp.subclasses.get(pk=int(ov.value))
            except grp.subclasses.model.DoesNotExist:
                pass

        return None
    def _linear_feats_for_level(cls_obj, grp, subclass, cls_level, base_feats=None):

        if not subclass:
            return []

        feats = []
        for f in (base_feats or []):
            if (getattr(f, "scope", "") == "subclass_feat"
                and getattr(f, "subclass_group_id", None) == grp.id
                and (subclass in f.subclasses.all())):
                lr = getattr(f, "level_required", None)
                ml = getattr(f, "min_level", None)
                if (ml is None or int(ml) <= int(cls_level)) and (lr is None or int(lr) <= int(cls_level)):
                    feats.append(f)

        if feats:
            return feats

        # Fallback: only when nothing is attached to this level (avoid leaking ungated L1 features)
        return list(
            ClassFeature.objects
                .filter(scope="subclass_feat", subclasses=subclass)
                .filter(
                    Q(subclass_group=grp) |              # if ClassFeature has FK subclass_group
                    Q(subclasses__group=grp)             # if we must hop via Subclass.group
                )
                .filter(
                    Q(level_required=cls_level) |
                    Q(level_required__isnull=True, min_level__lte=cls_level)
                )
                .exclude(level_required__isnull=True, min_level__isnull=True)
        )




    for trigger in gain_sub_feat_triggers:
        grp = trigger.subclass_group
        if not grp:
            continue

        field_name = f"feat_{trigger.pk}_subfeats"

        # ---------------- LINEAR ----------------
        if grp.system_type == SubclassGroup.SYSTEM_LINEAR:
            # use the GET-preview class/level for the UI preview here
            active_sub = _active_subclass_for_group(character, grp, level_form, base_feats)
            feats_now = _linear_feats_for_level(preview_cls, grp, active_sub, cls_level_after, base_feats)

            # Display-only: shows exactly what will be granted at this level
            feature_fields.append({
                "kind": "gain_subclass_feat",
                "label": f"Gain Subclass Feature – {grp.name}",
                "field": None,                   # read-only; granted on submit
                "group": grp,
                "subclass": active_sub,
                "eligible": list(feats_now),
                "system": grp.system_type,
            })
            continue  # important: skip to next trigger


        # ------------- MODULAR LINEAR -------------
        if grp.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
            # tiers unlocking right now
            # tiers available up to (and including) this class level
            unlock_tiers = _unlocked_tiers(grp, cls_level_after)


            # everything this character already took in THIS group
            taken_rows = (CharacterFeature.objects
                        .filter(character=character,
                                feature__scope='subclass_feat',
                                feature__subclass_group=grp)
                        .values_list('feature_id', 'subclass_id', 'feature__tier'))
            taken_feature_ids = {fid for (fid, _sid, _tier) in taken_rows}
            prev_tiers_by_sub = {}
            for (_fid, sid, tier) in taken_rows:
                if tier is None:
                    continue
                prev_tiers_by_sub.setdefault(sid, set()).add(tier)
            # union of eligible features across ALL subclasses in this group
            eligible_ids = []
            # union of eligible features across ALL subclasses in this group
            for sub in grp.subclasses.all():
                base = (
                    ClassFeature.objects
                    .filter(scope='subclass_feat', subclasses=sub)
                    .filter(Q(subclass_group=grp) | Q(subclasses__group=grp))
                    .filter(tier__in=unlock_tiers)
                    .filter(Q(level_required__isnull=True) | Q(level_required__lte=cls_level_after))
                    .filter(Q(min_level__isnull=True)      | Q(min_level__lte=cls_level_after))
                    .exclude(pk__in=taken_feature_ids)
                )


                for f in base:
                    if f.tier == 1 or ((f.tier - 1) in prev_tiers_by_sub.get(sub.pk, set())):
                        eligible_ids.append(f.pk)
                

            # Use the *subclass feature* model for the picker (NOT ClassFeat)
            eligible_qs = ClassFeature.objects.filter(pk__in=eligible_ids).order_by("name")

            level_form.fields[field_name] = forms.ModelMultipleChoiceField(
                label=f"Pick {grp.name} feature(s)",
                queryset=eligible_qs,
                required=bool(eligible_ids),
                widget=forms.CheckboxSelectMultiple
            )

            feature_fields.append({
                "kind": "gain_subclass_feat",
                "label": f"Gain Subclass Feature – {grp.name}",
                "field": level_form[field_name],
                "group": grp,
                "subclass": None,
                "eligible": list(eligible_qs),
                "system": grp.system_type,
            })


        # ------------- MODULAR MASTERY (TRIGGER-DRIVEN) -------------
        if grp.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
            from django.db.models import Count

            field_name = f"feat_{trigger.pk}_subfeats"

            # how many modules per tier (default 2 if not set)
            per = max(1, int(getattr(grp, "modules_per_mastery", 2)))

            # how many picks this trigger gives (usually 1)
            picks_per_trigger = _picks_for_trigger(trigger, preview_cls, cls_level_after)

            # the *gainer’s* cap for tier you may pick up to (None/0 = unlimited)
            gainer_cap = int(getattr(trigger, "mastery_rank", 0) or 0)  # 0/None => unbounded

            # what we’ve already taken (per subclass) for this group
            taken_by_sub = dict(
                CharacterFeature.objects.filter(
                    character=character,
                    feature__scope='subclass_feat',
                    feature__subclass_group=grp
                ).values('subclass_id').annotate(cnt=Count('id'))
                .values_list('subclass_id', 'cnt')
            )

            # current tier per subclass (start at tier 1; advance every 'per' modules)
            current_tier_by_sub = {}
            for sub in grp.subclasses.all():
                taken = int(taken_by_sub.get(sub.id, 0))
                current_tier_by_sub[sub.id] = 1 + (taken // per)

            # feature ids already owned in this group (avoid duplicates)
            owned_feat_ids = set(
                CharacterFeature.objects.filter(
                    character=character, feature__scope='subclass_feat',
                    feature__subclass_group=grp
                ).values_list('feature_id', flat=True)
            )

            # build eligible set across *all* subclasses
            eligible_ids = []
            for sub in grp.subclasses.all():
                # allowed tier for this subclass this time:
                # <= current tier, and <= trigger's cap if it exists
                allowed_cap = current_tier_by_sub[sub.id]
                if gainer_cap:
                    allowed_cap = min(allowed_cap, gainer_cap)

                q = ClassFeature.objects.filter(
                    scope='subclass_feat',
                    subclass_group=grp,
                    subclasses=sub
                )
                if allowed_cap:
                    q = q.filter(models.Q(mastery_rank__isnull=True) |
                                models.Q(mastery_rank__lte=allowed_cap))

                # NO level attachments — do not filter by ClassLevel; optionally keep min_level if you use it
                q = q.exclude(pk__in=owned_feat_ids)

                eligible_ids.extend(q.values_list('id', flat=True))

            eligible_qs = ClassFeature.objects.filter(pk__in=eligible_ids) \
                .order_by('mastery_rank', 'name')

            help_txt = (
                f"Pick exactly {picks_per_trigger} module"
                f"{'' if picks_per_trigger == 1 else 's'}. You can pick from any subclass. "
                f"Tiers per subclass now: "
                + ", ".join(
                    f"{s.name}≤{current_tier_by_sub.get(s.id,1)}"
                    + (f" (cap {gainer_cap})" if gainer_cap else "")
                    for s in grp.subclasses.all()
                )
            )

            # ALWAYS create the field (prevents KeyError on POST)
            level_form.fields[field_name] = forms.ModelMultipleChoiceField(
                label=f"Pick {grp.name} feature(s)",
                queryset=eligible_qs,
                required=(picks_per_trigger > 0),
                widget=forms.CheckboxSelectMultiple,
                help_text=help_txt,
            )

            feature_fields.append({
                "kind": "gain_subclass_feat",
                "label": f"Gain Subclass Feature – {grp.name}",
                "field": level_form[field_name],
                "group": grp,
                "subclass": None,   # no subclass choice in this system
                "eligible": list(eligible_qs),
                "system": grp.system_type,
                "mastery_meta": {
                    "picks_per_trigger": picks_per_trigger,
                    "modules_per_mastery": per,
                    "gainer_cap": gainer_cap or None,
                },
            })
            continue

    # --- PREVIEW: auto LINEAR subclass grants when the level has only subclass_feat attachments ---
    groups_with_trigger = {t.subclass_group_id for t in gain_sub_feat_triggers if getattr(t, "subclass_group_id", None)}

    for grp in subclass_groups:
        if grp.system_type != SubclassGroup.SYSTEM_LINEAR:
            continue
        if grp.id in groups_with_trigger:
            continue  # already handled via trigger UI

        # Are there subclass_feat features actually attached to this ClassLevel?
        attached_here = [
            f for f in (base_feats or [])
            if isinstance(f, ClassFeature)
            and (getattr(f, "scope", "") or "") == "subclass_feat"
            and getattr(f, "subclass_group_id", None) == grp.id
        ]
        if not attached_here:
            continue

        active_sub = _active_subclass_for_group(character, grp, level_form, base_feats)
        feats_now = _linear_feats_for_level(preview_cls, grp, active_sub, cls_level_after, base_feats)

        feature_fields.append({
            "kind": "gain_subclass_feat",
            "label": f"Gain Subclass Feature – {grp.name}",
            "field": None,                  # read-only preview
            "group": grp,
            "subclass": active_sub,
            "eligible": list(feats_now),    # exactly what this level grants for the chosen subclass
            "system": grp.system_type,
        })




    # ---- Restrict feat querysets by type + race/subrace + class name + tags ----
    # NOTE: Q must be imported at module level; do NOT import Q in this function.

    # A) class tag flags (is_martial / is_spellcaster) from CharacterClass.tags
    cls_tag_names   = set(preview_cls.tags.values_list("name", flat=True))
    is_martial      = any(t.lower() == "martial"     for t in cls_tag_names)
    is_spellcaster  = any(t.lower() == "spellcaster" for t in cls_tag_names)

    # B) race/subrace filter against free-text ClassFeat.race
    race_names = []
    if character.race and getattr(character.race, "name", None):
        race_names.append(character.race.name)
    if character.subrace and getattr(character.subrace, "name", None):
        race_names.append(character.subrace.name)

    # allow empty race, or match tokens of race/subrace
    race_q = Q(race__exact="") | Q(race__isnull=True)
    if race_names:
        token_regexes = [rf'(^|[,;/\s]){re.escape(n)}([,;/\s]|$)' for n in race_names]
        race_token_re = "(" + ")|(".join(token_regexes) + ")"
        race_q |= Q(race__iregex=race_token_re)

    # C) GENERAL feats – only feat_type=General + race filter
    if "general_feat" in level_form.fields:
        gf_qs = level_form.fields["general_feat"].queryset
        if gf_qs is not None:
            level_form.fields["general_feat"].queryset = (
                gf_qs.filter(feat_type__iexact="General")
                    .filter(race_q)
                    .order_by("name")
            )

    if "class_feat_pick" in level_form.fields:
        # Use the same target class/level we validated with
        target_cls = posted_cls if request.method == 'POST' else preview_cls
        cls_after  = cls_level_for_validate
        cls_name   = target_cls.name

        class_tags = [t.lower() for t in target_cls.tags.values_list("name", flat=True)]
        tokens = [cls_name] + class_tags
        if "spellcaster" in class_tags:
            tokens += ["spellcaster", "spellcasting", "caster"]
        if "martial" in class_tags:
            tokens += ["martial"]

        token_res = [rf'(^|[,;/\s]){re.escape(tok)}([,;/\s]|$)' for tok in tokens if tok]
        any_token_re = "(" + ")|(".join(token_res) + ")" if token_res else None

        base = ClassFeat.objects.filter(feat_type__iexact="Class")
        membership_q = (
            Q(class_name__iregex=any_token_re) |
            Q(tags__iregex=any_token_re) |
            Q(class_name__regex=r'(?i)\b(all|any)\s+classes?\b') |
            Q(class_name__exact="") | Q(class_name__isnull=True)
        ) if any_token_re else (
            Q(class_name__regex=r'(?i)\b(all|any)\s+classes?\b') |
            Q(class_name__exact="") | Q(class_name__isnull=True)
        )

        qs = base.filter(membership_q)

        eligible_ids = [
            f.pk for f in qs
            if parse_req_level(getattr(f, "level_prerequisite", "")) <= cls_after
        ]
        if not eligible_ids:
            cls_re = rf'(^|[,;/\s]){re.escape(cls_name)}([,;/\s]|$)'
            relaxed = base.filter(
                Q(class_name__iregex=cls_re) |
                Q(class_name__regex=r'(?i)\b(all|any)\s+classes?\b') |
                Q(class_name__exact="") | Q(class_name__isnull=True)
            )
            eligible_ids = [
                f.pk for f in relaxed
                if parse_req_level(getattr(f, "level_prerequisite", "")) <= cls_after
            ]

        level_form.fields["class_feat_pick"].queryset = (
            ClassFeat.objects.filter(pk__in=eligible_ids).order_by("name")
        )


    # E) SKILL feats (if/when you add a field) – only feat_type=Skill + race filter
    if "skill_feat_pick" in level_form.fields:
        sf_qs = level_form.fields["skill_feat_pick"].queryset or ClassFeat.objects.none()
        # Base type/race filter
        sf_qs = sf_qs.filter(feat_type__iexact="Skill").filter(race_q)

        # Optional: restrict to class membership/tags if your data uses them (mirrors class_feat rules)
        target_cls = posted_cls if request.method == 'POST' else preview_cls
        if target_cls:
            class_tags = [t.lower() for t in target_cls.tags.values_list("name", flat=True)]
            tokens = [target_cls.name] + class_tags
            if "spellcaster" in class_tags: tokens += ["spellcaster", "spellcasting", "caster"]
            if "martial" in class_tags: tokens += ["martial"]
            token_res = [rf'(^|[,;/\s]){re.escape(tok)}([,;/\s]|$)' for tok in tokens if tok]
            any_token_re = "(" + ")|(".join(token_res) + ")" if token_res else None
            if any_token_re:
                sf_qs = sf_qs.filter(
                    Q(class_name__iregex=any_token_re) |
                    Q(tags__iregex=any_token_re) |
                    Q(class_name__regex=r'(?i)\b(all|any)\s+classes?\b') |
                    Q(class_name__exact="") | Q(class_name__isnull=True)
                )

        sf_qs = sf_qs.order_by("name")
        level_form.fields["skill_feat_pick"].queryset = sf_qs

        # Convenience: auto-select if exactly one option and a pick is required
        picks_required = getattr(skill_grant, "num_picks", 0) and int(skill_grant.num_picks) > 0
        if request.method == "POST" and picks_required and sf_qs.count() == 1 and not request.POST.getlist("skill_feat_pick"):
            _post = request.POST.copy()
            only_id = str(sf_qs.first().pk)
            # ModelChoiceField posts a single value; MultipleChoice posts list
            if isinstance(level_form.fields["skill_feat_pick"], forms.ModelMultipleChoiceField):
                _post.setlist("skill_feat_pick", [only_id])
            else:
                _post["skill_feat_pick"] = only_id
            request.POST = _post
            level_form.data = _post
    # --- INLINE save for a skill's Formula / Final (primary/secondary) -------------
    if request.method == "POST" and request.POST.get("save_skill_override") and can_edit:
        packed = (request.POST.get("save_skill_override") or "").strip()  # e.g. "sk_12:1"
        if ":" not in packed:
            messages.error(request, "Invalid override target.")
            return redirect('characters:character_detail', pk=pk)
        id_key, col = packed.split(":", 1)
        col = col.strip()
        # fields are namespaced like ov_formula_<id_key>_<col>
        form_key  = f"ov_formula_{id_key}_{col}"
        final_key = f"ov_final_{id_key}_{col}"
        note_key  = f"ov_reason_{id_key}_{col}"

        formula = (request.POST.get(form_key) or "").strip()
        final_s = (request.POST.get(final_key) or "").strip()
        reason  = (request.POST.get(note_key) or "").strip()
        okey    = f"skill:{id_key}:{col}"

        if formula == "" and final_s == "":
            messages.info(request, "Nothing to save.")
            return redirect('characters:character_detail', pk=pk)
        if not reason:
            messages.error(request, "Reason is required.")
            return redirect('characters:character_detail', pk=pk)

        # Save/Clear FORMULA
        if formula == "":
            CharacterFieldOverride.objects.filter(character=character, key=f"formula:{okey}").delete()
            CharacterFieldNote.objects.filter(character=character, key=f"formula:{okey}").delete()
        else:
            CharacterFieldOverride.objects.update_or_create(
                character=character, key=f"formula:{okey}", defaults={"value": formula}
            )
            CharacterFieldNote.objects.update_or_create(
                character=character, key=f"formula:{okey}", defaults={"note": reason}
            )

        # Save/Clear FINAL
        if final_s == "":
            CharacterFieldOverride.objects.filter(character=character, key=f"final:{okey}").delete()
            CharacterFieldNote.objects.filter(character=character, key=f"final:{okey}").delete()
        else:
            try:
                final_i = int(final_s)
            except ValueError:
                messages.error(request, "Final must be a number.")
                return redirect('characters:character_detail', pk=pk)
            CharacterFieldOverride.objects.update_or_create(
                character=character, key=f"final:{okey}", defaults={"value": str(final_i)}
            )
            CharacterFieldNote.objects.update_or_create(
                character=character, key=f"final:{okey}", defaults={"note": reason}
            )

        messages.success(request, "Override saved.")
        return redirect('characters:character_detail', pk=pk)

    # --- NEW: Save/Clear a proficiency TIER override for a code (e.g., "armor","dodge","dc") ---
    if request.method == "POST" and request.POST.get("save_prof_tier_override") and can_edit:
        code   = (request.POST.get("prof_code") or "").strip()      # e.g. "armor"
        tier_s = (request.POST.get("prof_tier_pk") or "").strip()   # ProficiencyLevel.pk
        reason = (request.POST.get("prof_tier_reason") or "").strip()
        if not code:
            messages.error(request, "Missing proficiency code.")
            return redirect('characters:character_detail', pk=pk)
        if not reason:
            messages.error(request, "Reason is required.")
            return redirect('characters:character_detail', pk=pk)

        key = f"prof_tier:{code}"
        if tier_s == "":
            # clear override
            CharacterFieldOverride.objects.filter(character=character, key=key).delete()
            CharacterFieldNote.objects.filter(character=character, key=key).delete()
            messages.success(request, f"{code.title()} tier override cleared.")
        else:
            if not tier_s.isdigit() or not ProficiencyLevel.objects.filter(pk=int(tier_s)).exists():
                messages.error(request, "Invalid tier selected.")
                return redirect('characters:character_detail', pk=pk)
            CharacterFieldOverride.objects.update_or_create(
                character=character, key=key, defaults={"value": str(int(tier_s))}
            )
            CharacterFieldNote.objects.update_or_create(
                character=character, key=key, defaults={"note": reason}
            )
            messages.success(request, f"{code.title()} tier override saved.")
        return redirect('characters:character_detail', pk=pk)

    if request.method == "POST" and request.POST.get("clear_prof_tier_override") and can_edit:
        code = (request.POST.get("clear_prof_tier_override") or "").strip()
        if code:
            CharacterFieldOverride.objects.filter(character=character, key=f"prof_tier:{code}").delete()
            CharacterFieldNote.objects.filter(character=character, key=f"prof_tier:{code}").delete()
            messages.success(request, f"{code.title()} tier override cleared.")
        return redirect('characters:character_detail', pk=pk)




    # ── 5) BUILD feature_fields FOR TEMPLATE ───────────────────────────────
    subclass_feats_at_next = {}
    for grp in subclass_groups:
        unlock_tiers = None
        if grp.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
            unlock_tiers = _unlocked_tiers(grp, cls_level_after)

        for sc in grp.subclasses.all():
            qs = ClassFeature.objects.filter(
                scope='subclass_feat',
                subclasses=sc
            ).filter(
                Q(subclass_group=grp) | Q(subclasses__group=grp)
            )


            if grp.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
                feats = list(
                    qs.filter(tier__in=unlock_tiers)
                    .filter(Q(level_required__isnull=True) | Q(level_required__lte=cls_level_after))
                    .filter(Q(min_level__isnull=True)      | Q(min_level__lte=cls_level_after))
                    .order_by('name')
                )

            elif grp.system_type == SubclassGroup.SYSTEM_LINEAR:
                feats = _linear_feats_for_level(preview_cls, grp, sc, cls_level_after, base_feats)

            elif grp.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
                per = max(1, int(getattr(grp, "modules_per_mastery", 2)))
                taken = CharacterFeature.objects.filter(
                    character=character, subclass=sc, feature__scope='subclass_feat'
                ).count()
                current_rank = 1 + (taken // per) 

                feats = list(
                    qs.filter(
                        models.Q(mastery_rank__isnull=True) |
                        models.Q(mastery_rank__lte=current_rank)
                    ).order_by('name')
                )

            else:  # SubclassGroup.SYSTEM_MODULAR_MASTERY
                rules = sc.modular_rules or {}
                modules_per_mastery = int(rules.get('modules_per_mastery', 2))
                taken = CharacterFeature.objects.filter(
                    character=character, subclass=sc, feature__scope='subclass_feat'
                ).count()
                current_mastery = taken // max(1, modules_per_mastery)

                feats = list(
                    qs.filter(Q(mastery_rank__isnull=True) | Q(mastery_rank__lte=current_mastery))
                    .filter(Q(min_level__isnull=True) | Q(min_level__lte=cls_level_after))
                    .order_by('name')
                )
            sc.feats_next = feats
            subclass_feats_at_next[(grp.pk, sc.pk)] = [f.pk for f in feats]  # optional, if you want an index




    for feat in to_choose:
        if isinstance(feat, ClassFeature) and feat.scope == 'subclass_choice':
            fn = f"feat_{feat.pk}_subclass"
            # Use the *same* group instance we enriched earlier (so its subclasses have .feats_next)
            grp_pk = feat.subclass_group_id
            grp_enriched = next((g for g in subclass_groups if g.pk == grp_pk), feat.subclass_group)
            feature_fields.append({
                "kind":  "subclass_choice",
                "label": f"Choose {grp_enriched.name}",
                "field": level_form[fn],
                "group": grp_enriched,
            })

        elif isinstance(feat, ClassFeature) and feat.has_options:
            fn = f"feat_{feat.pk}_option"
            feature_fields.append({
                "kind":  "option",
                "label": feat.name,
                "field": level_form[fn],
                "feature": feat,  
            })
               
    field_overrides = {o.key: o.value for o in character.field_overrides.all()}
    field_notes     = {n.key: n.note  for n in character.field_notes.all()}

    # ------- OVERRIDES map (includes numbers the user sets with a reason) -------
    overrides = {o.key: o.value for o in character.field_overrides.all()}

    # Base profs from your resolver
    prof_by_code = {r["type_code"]: r for r in _current_proficiencies_for_character(character)}

    # 1) NEW: apply TIER override first (changes tier_name + modifier)
    #    Key format: "prof_tier:{code}" -> value is ProficiencyLevel.pk
    tier_rows = ProficiencyLevel.objects.in_bulk()  # {pk: ProficiencyLevel}
    for code, row in prof_by_code.items():
        tier_pk = overrides.get(f"prof_tier:{code}")
        if tier_pk and str(tier_pk).isdigit():
            pl = tier_rows.get(int(tier_pk))
            if pl:
                row["modifier"]  = int(pl.bonus or 0)
                row["tier_name"] = (pl.name or "").title()
                row["source"]    = "Tier override"

    # 2) (Existing) numeric modifier override still supported and wins last
    for code, row in prof_by_code.items():
        ov = overrides.get(f"prof:{code}")
        if ov not in (None, ""):
            try:
                row["modifier"] = int(ov)
                row["source"]   = "Override"
            except ValueError:
                pass

    # Keep list form for template, and a **fresh** by_code after tier overrides
    proficiency_summary = list(prof_by_code.values())
    by_code = {r["type_code"]: r for r in proficiency_summary}

    half_lvl = _half_level_total(character.level)

    def hl_if_trained(code: str) -> int:
        r = by_code.get(code)
        if not r:
            return 0
        # Respect the (possibly overridden) tier_name
        return half_lvl if not _is_untrained_name(r.get("tier_name")) else 0


    by_code = {r["type_code"]: r for r in proficiency_summary}
    def hl_if_trained(code: str) -> int:
        r = by_code.get(code)
        if not r: return 0
        return half_lvl if not _is_untrained_name(r.get("tier_name")) else 0
    # Pull armor choices from the Armor model
    # ---- Effective proficiency for the EQUIPPED ARMOR (per-item/per-group) ----
    selected_armor = None
    try:
        equipped_id = overrides.get("equipped_armor_id")
        # default to override value if set; fall back to 0
        armor_value = int(overrides.get("armor_value") or 0)
        if equipped_id:
            selected_armor = Armor.objects.get(pk=int(equipped_id))
            armor_value = selected_armor.armor_value  # authoritative if an armor is selected
    except (ValueError, Armor.DoesNotExist):
        armor_value = 0
        selected_armor = None

    armor_prof = {"bonus": 0, "is_proficient": False, "name": "Untrained"}
    if selected_armor:
        armor_prof = _effective_class_prof_for_item(
            character, "armor",
            armor_group=_armor_group_for(selected_armor),
            armor_item_id=selected_armor.id
        )
    # ½ level only if actually proficient with that armor
    half_armor = half_lvl if armor_prof["is_proficient"] else 0


    # Armor picker: list + currently selected (by override)
    armor_list = list(Armor.objects.all().order_by('type','name').values('id','name','armor_value'))
    # Use overrides to determine equipped armor/value BEFORE computing derived stats

    str_mod = _abil_mod(character.strength)
    dex_mod = _abil_mod(character.dexterity)
    con_mod = _abil_mod(character.constitution)
    wis_mod = _abil_mod(character.wisdom)
    # pick a “primary class” = most levels; may be None
    primary_cp = max(class_progress, key=lambda cp: cp.levels, default=None)
    key_abil_names = []
    if primary_cp:
        key_abil_names = list(primary_cp.character_class.key_abilities.values_list("name", flat=True))

    # per-type proficiency bonuses (after override above)

    # perception/prof
    prof_perception = prof_by_code.get("perception", {"modifier": 0})["modifier"]
    prof_armor      = prof_by_code.get("armor",     {"modifier": 0})["modifier"]
    prof_dodge      = prof_by_code.get("dodge",     {"modifier": 0})["modifier"]
    prof_dc         = prof_by_code.get("dc",        {"modifier": 0})["modifier"]
    prof_reflex     = prof_by_code.get("reflex",    {"modifier": 0})["modifier"]
    prof_fort       = prof_by_code.get("fortitude", {"modifier": 0})["modifier"]
    prof_will       = prof_by_code.get("will",      {"modifier": 0})["modifier"]
    prof_weapon     = prof_by_code.get("weapon",    {"modifier": 0})["modifier"]

    # HP/Temp HP resilient to model differences
    # replace the three lines that compute hp_current/hp_max/temp_hp
    # HP per spec: race_hp + (class hit die + CON mod) * level
    # primary_cp already computed earlier as the class with the most levels
    race_hp = int(getattr(character, "race_hp", 0) or 0)  # uses Character.race_hp if present
    hit_die = int(getattr(primary_cp.character_class, "hit_die", 0)) if primary_cp else 0
    hp_max_base = race_hp + (hit_die + con_mod) * character.level

    # allow an override to force hp_max if the user sets one
    hp_max = int(overrides.get("hp_max", hp_max_base))

    # current and temp can be overridden or fall back to model fields
    hp_current = int((overrides.get("HP")      or getattr(character, "HP", 0)) or 0)
    temp_hp    = int((overrides.get("temp_HP") or getattr(character, "temp_HP", 0)) or 0)

    dex_for_dodge = dex_mod
    if selected_armor and selected_armor.dex_cap is not None:
        dex_for_dodge = min(dex_mod, int(selected_armor.dex_cap))

    derived = {
        "half_level":      half_lvl,
        "armor_total":     int(overrides.get("armor_value") or 0) + armor_prof["bonus"] + half_armor,        
        "dodge_total":     10 + dex_for_dodge + prof_dodge + hl_if_trained("dodge"),
        "reflex_total":    dex_mod + prof_reflex + hl_if_trained("reflex"),
        "fortitude_total": con_mod + prof_fort   + hl_if_trained("fortitude"),
        "will_total":      wis_mod + prof_will   + hl_if_trained("will"),
        "perception_total": prof_perception + hl_if_trained("perception"),  # (no ability in your model)
        "weapon_base":     prof_weapon + hl_if_trained("weapon"),
        "weapon_with_str": prof_weapon + hl_if_trained("weapon") + str_mod,
        "weapon_with_dex": prof_weapon + hl_if_trained("weapon") + dex_mod,
        "spell_dcs":       [],
    }

    LABELS = dict(PROFICIENCY_TYPES)
    def _hl(code): return hl_if_trained(code)
    defense_rows = []

    def add_row(code, abil_name=None, abil_mod_val=0, label=None, base_const=0,
                prof_override=None, half_override=None):
        r = prof_by_code.get(code, {"tier_name":"—","modifier":0,"source":"—"})
        prof = int(prof_override if prof_override is not None else r["modifier"])
        half = int(half_override if half_override is not None else _hl(code))
        # ...rest of function unchanged, but use `prof` and `half` from above...


        # default system formula
        total_sys = base_const + prof + half + (abil_mod_val if abil_name else 0)
        formula_h = []
        values_h  = []
        if base_const: formula_h.append("base"); values_h.append(str(base_const))
        formula_h += ["prof","½ level"]
        values_h  += [str(prof), str(half)]
        if abil_name:
            formula_h.append(f"{abil_name[:3]} mod")
            values_h.append(str(abil_mod_val))

        # context for user formulas
        ctx = {
            "base": base_const, "prof": prof, "half": half,
            "strength": _abil_mod(character.strength), "dexterity": _abil_mod(character.dexterity),
            "constitution": _abil_mod(character.constitution), "intelligence": _abil_mod(character.intelligence),
            "wisdom": _abil_mod(character.wisdom), "charisma": _abil_mod(character.charisma),
            "str_mod": _abil_mod(character.strength), "dex_mod": _abil_mod(character.dexterity),
            "con_mod": _abil_mod(character.constitution), "int_mod": _abil_mod(character.intelligence),
            "wis_mod": _abil_mod(character.wisdom), "cha_mod": _abil_mod(character.charisma),
            "level": character.level, "floor": math.floor, "ceil": math.ceil, "min": min, "max": max, "int": int, "round": round,
        }

        # (3) apply a per-stat formula override if present
        used_formula = " + ".join(formula_h)
        total_calc   = total_sys
        try:
            expr = _formula_override(f"prof:{code}")
            if expr:
                total_calc   = int(eval(expr, {"__builtins__": {}}, ctx))
                used_formula = expr
        except Exception:
            # keep system total on any error
            pass

        # (4) allow a direct final override
        final = _final_override(f"prof:{code}")
        if final is not None:
            total_calc = final

        debug = {
            "formula": used_formula,
            "values":  " + ".join(values_h),
            "total":   total_calc,
            "vars": [
                *([{"name": "base", "value": base_const, "note": "Base"}] if base_const else []),
                {"name": "prof", "value": prof, "note": r.get("tier_name","")},
                {"name": "½ level", "value": half, "note": "applies if trained"},
                *([{"name": f"{(abil_name or '')[:3]} mod", "value": abil_mod_val, "note": abil_name}] if abil_name else []),
            ],
        }

        defense_rows.append({
            "code":   code,
            "type":   label or LABELS.get(code, code).title(),
            "tier":   r["tier_name"],
            "formula": used_formula,
            "values":  debug["values"],
            "total_s": _fmt(total_calc),
            "source": r["source"],
            "calc": {
                "formula": used_formula,
                "parts": [
                    *([{"key": "base", "label": "Base", "value": base_const}] if base_const else []),
                    {"key": "prof", "label": "Proficiency", "value": prof, "note": r.get("tier_name","")},
                    {"key": "half", "label": "½ level", "value": half},
                    *([{"key": "abil", "label": f"{(abil_name or '')[:3]} mod", "value": abil_mod_val, "note": abil_name}] if abil_name else []),
                ],
                "total": total_calc,
            },
            # Provide debug as JSON for the modal viewer
            "debug_json": json.dumps(debug),
        })


    add_row("dodge",  "Dexterity", dex_mod, label="Dodge", base_const=10)   # ← 10 + DEX + prof + ½ level
    add_row("reflex", "Dexterity", dex_mod, label="Reflex")
    add_row("fortitude","Constitution", con_mod, label="Fortitude")
    add_row("will",   "Wisdom",   wis_mod, label="Will")
    add_row("perception",               label="Perception")  # (no ability in your model)
    add_row("initiative",               label="Initiative")  # (no ability in your model)
    add_row("weapon",                   label="Weapon (base)")

    # earlier you computed armor_value already
    add_row(
        "armor", label="Armor", base_const=armor_value,
        prof_override=armor_prof["bonus"], half_override=half_armor
    )
    by_slot = {
        e.slot_index: e
        for e in character.equipped_weapons.select_related("weapon").all()
    }


    if by_slot.get(1):
        main_w = by_slot[1].weapon
        main_prof = _effective_class_prof_for_item(
            character, "weapon",
            weapon_group=_weapon_group_for(main_w),
            weapon_item_id=main_w.id
        )
        half_main = half_lvl if main_prof["is_proficient"] else 0
        prof_weapon = main_prof["bonus"]      # override generic
        def _half_weapon(): return half_main  # tiny shim

    else:
        # keep existing generic behavior
        def _half_weapon(): return hl_if_trained("weapon")
        prof_weapon = prof_by_code.get("weapon", {"modifier": 0})["modifier"]

    attack_rows = [
        {
            "label": "Weapon (base)",
            "total_s": _fmt(prof_weapon + _half_weapon()),
            "formula": "prof + ½ level",
            "values": f"{_fmt(prof_weapon)} + {_fmt(_half_weapon())}",
            "calc": {
                "formula": "prof + half",
                "parts": [
                    {"key":"prof","label":"Proficiency","value":prof_weapon,
                    "note": prof_by_code.get('weapon', {}).get('tier_name','')},
                    {"key":"half","label":"½ level","value":_half_weapon()},
                ],
                "total": prof_weapon + _half_weapon(),
            },
        },
        {
            "label": "Weapon (STR)",
            "total_s": _fmt(prof_weapon + _half_weapon() + str_mod),
            "formula": "prof + ½ level + STR mod",
            "values": f"{_fmt(prof_weapon)} + {_fmt(_half_weapon())} + {_fmt(str_mod)}",
            "calc": {
                "formula": "prof + half + abil",
                "parts": [
                    {"key":"prof","label":"Proficiency","value":prof_weapon,
                    "note": prof_by_code.get('weapon', {}).get('tier_name','')},
                    {"key":"half","label":"½ level","value":_half_weapon()},
                    {"key":"abil","label":"STR mod","value":str_mod},
                ],
                "total": prof_weapon + _half_weapon() + str_mod,
            },
        },
        {
            "label": "Weapon (DEX)",
            "total_s": _fmt(prof_weapon + _half_weapon() + dex_mod),
            "formula": "prof + ½ level + DEX mod",
            "values": f"{_fmt(prof_weapon)} + {_fmt(_half_weapon())} + {_fmt(dex_mod)}",
            "calc": {
                "formula": "prof + half + abil",
                "parts": [
                    {"key":"prof","label":"Proficiency","value":prof_weapon,
                    "note": prof_by_code.get('weapon', {}).get('tier_name','')},
                    {"key":"half","label":"½ level","value":_half_weapon()},
                    {"key":"abil","label":"DEX mod","value":dex_mod},
                ],
                "total": prof_weapon + _half_weapon() + dex_mod,
            },
        },
    ]



    # Spell/DC rows (one per key ability)
    # Build Spell/DC values from key abilities, then produce rows for the template
    derived["spell_dcs"] = []
    for abil in key_abil_names:
        score = getattr(character, abil.lower(), 10)
        mod   = _abil_mod(score)
        derived["spell_dcs"].append({
            "ability": abil,
            "value": 10 + mod + prof_dc + hl_if_trained("dc"),
        })
    # Build DC rows from the actual spellcasting features we just computed
    spell_dc_rows = []

    totals = _formula_totals(character)
    for b in spellcasting_blocks:
        origin_key = (b.get("list") or b.get("origin") or "").lower()
        fill = totals.get(origin_key, {}).get("cantrips_known")
        if fill is not None and int(b.get("cantrips", 0) or 0) == 0:
            b["cantrips"] = int(fill)




    # pick a main DC for the left card (first available)





    # ------- Build the Skills table (all skills + all subskills) -------
    order = Case(
        When(name__iexact="Untrained", then=0),
        When(name__iexact="Trained",   then=1),
        When(name__iexact="Expert",    then=2),
        When(name__iexact="Master",    then=3),
        When(name__iexact="Legendary", then=4),
        default=5, output_field=IntegerField()
    )
    prof_levels = list(
        ProficiencyLevel.objects
            .filter(name__in=FIVE_TIERS)
            .order_by(order, "bonus")
    )

    untrained_level = next((pl for pl in prof_levels if _is_untrained_name(pl.name)), None)
    ct_skill    = ContentType.objects.get_for_model(Skill)
    ct_sub      = ContentType.objects.get_for_model(SubSkill)

    existing = {}  # (ctype_id, obj_id) -> ProficiencyLevel
    for sp in character.skill_proficiencies.select_related("proficiency").all():
        existing[(sp.selected_skill_type_id, sp.selected_skill_id)] = sp.proficiency

    def current_prof_for(obj):
        ctype_id = (ct_sub.id if isinstance(obj, SubSkill) else ct_skill.id)
        return existing.get((ctype_id, obj.pk))

    all_skill_rows = []
    
    for sk in Skill.objects.prefetch_related("subskills").order_by("name"):
        abil1 = sk.ability       # e.g. "strength"
        abil2 = sk.secondary_ability  # may be None
        a1_mod = _abil_mod(getattr(character, abil1, 10))
        a2_mod = _abil_mod(getattr(character, abil2, 10)) if abil2 else None

        # display each subskill; if none exist, show the skill itself
        subs = list(sk.subskills.all())
        targets = subs or [sk]
        for obj in targets:
            is_sub = isinstance(obj, SubSkill)
            label  = f"{sk.name} – {obj.name}" if is_sub else sk.name
            prof = current_prof_for(obj) or untrained_level
            pbonus = prof.bonus if prof else 0

            # half level only if not Untrained
            h = half_lvl if (prof and not _is_untrained_name(prof.name)) else 0

            total1 = pbonus + h + a1_mod
            total2 = (pbonus + h + a2_mod) if a2_mod is not None else None

            row = {
                "id_key": (f"sub_{obj.pk}" if is_sub else f"sk_{sk.pk}"),
                "is_sub": is_sub,
                "skill_id": sk.pk,
                "sub_id": (obj.pk if is_sub else None),
                "label": label,
                "ability1":  abil1.title(),
                "ability2":  abil2.title() if abil2 else None,
                "prof_id":   (prof.pk if prof else None),
                "prof_name": (prof.name if prof else "Untrained"),
                "prof_bonus": pbonus,
                "mod1":      a1_mod,
                "mod2":      a2_mod,
                "half":      h,      # 0 for Untrained
                "total1":    total1,
                "total2":    total2,
            }
            row["tier_choices"] = [{"id": pl.pk, "name": pl.name} for pl in prof_levels]
            # --- Base human-readable formulae like Combat ---
            def _skill_formula(abil_label, abil_mod):
                f = "prof + ½ level" + (f" + {abil_label[:3]} mod" if abil_label else "")
                v = f"{row['prof_bonus']} + {row['half']}" + (f" + {abil_mod}" if abil_label else "")
                return f, v

            row["formula1"], row["values1"] = _skill_formula(row["ability1"], row["mod1"])
            row["formula2"], row["values2"] = (
                _skill_formula(row["ability2"], row["mod2"]) if row["ability2"] is not None else (None, None)
            )

            # Keep system totals before overrides (so relative formulas like '+1' can add to them)
            sys1 = row["prof_bonus"] + row["half"] + (row["mod1"] or 0)
            sys2 = (row["prof_bonus"] + row["half"] + (row["mod2"] or 0)) if row["mod2"] is not None else None

            ctx = {
                "prof": row["prof_bonus"], "half": row["half"], "level": character.level,
                "strength": _abil_mod(character.strength), "dexterity": _abil_mod(character.dexterity),
                "constitution": _abil_mod(character.constitution), "intelligence": _abil_mod(character.intelligence),
                "wisdom": _abil_mod(character.wisdom), "charisma": _abil_mod(character.charisma),
                "str_mod": _abil_mod(character.strength), "dex_mod": _abil_mod(character.dexterity),
                "con_mod": _abil_mod(character.constitution), "int_mod": _abil_mod(character.intelligence),
                "wis_mod": _abil_mod(character.wisdom), "cha_mod": _abil_mod(character.charisma),
                "floor": math.floor, "ceil": math.ceil, "min": min, "max": max, "int": int, "round": round,
            }

            def _note_for(k):
                n = CharacterFieldNote.objects.filter(character=character, key=k).first()
                return (n.note or "").strip() if n else ""

            # Apply FORMULA / FINAL overrides (col 1)
            key1 = f"skill:{row['id_key']}:1"
            expr1 = _formula_override(key1)  # -> value for "formula:key"
            if expr1:
                s = expr1.strip()
                n = _note_for(f"formula:{key1}")
                try:
                    if s[0:1] in {"+", "-"}:
                        adj = int(eval(_normalize_formula(s), {"__builtins__": {}}, ctx))
                        row["total1"] = sys1 + adj
                        row["formula1"] = f"{row['formula1']} {s}{f' ({n})' if n else ''}"
                    else:
                        val = int(eval(_normalize_formula(s), {"__builtins__": {}}, ctx))
                        row["total1"] = val
                        row["formula1"] = f"{s}{f' ({n})' if n else ''}"
                except Exception:
                    pass
            final1 = _final_override(key1)    # -> value for "final:key"
            if final1 is not None:
                n = _note_for(f"final:{key1}")
                # Keep the visible formula trail, append a Final marker
                row["formula1"] = f"{row['formula1']} → Final {final1}{f' ({n})' if n else ''}"
                row["total1"] = final1

            # Apply FORMULA / FINAL overrides (col 2) if present
            if row["ability2"] is not None:
                key2 = f"skill:{row['id_key']}:2"
                expr2 = _formula_override(key2)
                if expr2:
                    s = expr2.strip()
                    n = _note_for(f"formula:{key2}")
                    try:
                        if s[0:1] in {"+", "-"}:
                            adj = int(eval(_normalize_formula(s), {"__builtins__": {}}, ctx))
                            row["total2"] = (sys2 or 0) + adj
                            row["formula2"] = f"{row['formula2']} {s}{f' ({n})' if n else ''}"
                        else:
                            val = int(eval(_normalize_formula(s), {"__builtins__": {}}, ctx))
                            row["total2"] = val
                            row["formula2"] = f"{s}{f' ({n})' if n else ''}"
                    except Exception:
                        pass
                final2 = _final_override(key2)
                if final2 is not None:
                    n = _note_for(f"final:{key2}")
                    row["formula2"] = f"{row['formula2']} → Final {final2}{f' ({n})' if n else ''}"
                    row["total2"] = final2


            # --- LOR upgrade metadata for the UI ---
            current_name = _tier_name(prof)                 # e.g., "Trained"
            next_tier    = _next_tier_name(current_name)    # e.g., "Expert" or None
            row["next_tier"] = next_tier
            if next_tier:
                row["upgrade_cost"] = _upgrade_cost(current_name)
                row["min_level_for_next"] = _min_level_to_reach(next_tier)
                row["can_reach_next_now"] = (character.level >= row["min_level_for_next"])
            else:
                row["upgrade_cost"] = None
                row["min_level_for_next"] = None
                row["can_reach_next_now"] = False

            # Retrain is allowed for anything above Untrained
            row["can_retrain"] = (current_name != "Untrained")
            # Simple preview: if downgrading one step, refund the cost of the step you're undoing
            if row["can_retrain"]:
                # new tier after retrain
                idx = LOR_TIER_ORDER.index(current_name)
                new_name = LOR_TIER_ORDER[idx-1]
                row["refund_preview"] = LOR_UPGRADE_COST[new_name]

            all_skill_rows.append(row)
    # attach tier-change history strings to each row for the template

    # --- NEW (attach tier-change history strings to each row for the template) ---
    _hist_qs = CharacterFieldNote.objects.filter(
        character=character, key__startswith="skill_prof_hist:"
    ).values_list("key", "note")

    _hist_by_idkey = {}
    for k, v in _hist_qs:
        parts = (k or "").split(":")
        # k format: "skill_prof_hist:<id_key>:<uid>"
        if len(parts) >= 3:
            _hist_by_idkey.setdefault(parts[1], []).append(v)

    for _r in all_skill_rows:
        _r["prof_history"] = _hist_by_idkey.get(_r["id_key"], [])


    hist_notes = list(
        CharacterFieldNote.objects
        .filter(character=character, key__startswith="skill_prof_hist:")
        .values_list("key", "note")
    )
    by_skill_hist = {}
    for k, v in hist_notes:
        # k = "skill_prof_hist:<id_key>:<uid>"
        parts = (k or "").split(":")
        if len(parts) >= 3:
            by_skill_hist.setdefault(parts[1], []).append((k, v))

    for row in all_skill_rows:
        row["prof_history"] = [v for (_k, v) in by_skill_hist.get(row["id_key"], [])]

    # Apply per-skill multi-entry deltas; expose list for UI removal/history
    all_delta_rows = list(
        CharacterFieldOverride.objects
        .filter(character=character, key__startswith="skill_delta:")
        .order_by("id")
    )
    notes_by_key = {
        n.key: n.note for n in CharacterFieldNote.objects
        .filter(character=character, key__startswith="skill_delta:")
    }

    # group by id_key
    from collections import defaultdict
    deltas_map = defaultdict(list)  # id_key -> list[{"key": full_key, "value": int, "note": str}]
    for o in all_delta_rows:
        # expected pattern: "skill_delta:<id_key>:<uid>"
        parts = (o.key or "").split(":")
        if len(parts) >= 3:
            id_key = parts[1]
            note = (notes_by_key.get(o.key) or "").strip()
            try:
                val = int(o.value)
            except Exception:
                continue
            deltas_map[id_key].append({"key": o.key, "value": val, "note": note})

    for row in all_skill_rows:
        mods = deltas_map.get(row["id_key"], [])
        row["modifications"] = mods                 # for listing & removal UI
        adj_total = sum(m["value"] for m in mods)
        row["adjustment_total"] = adj_total         # optional display

        if mods:
            # apply to totals & append "(+X (reason))" segments in order
            def _append(seg, val, note):
                sgn = "+" if val >= 0 else ""
                return f"{seg} {sgn}{val}{f' ({note})' if note else ''}"

            if row.get("total1") is not None:
                row["total1"] = (row["total1"] or 0) + adj_total
                for m in mods:
                    row["formula1"] = _append(row["formula1"], m["value"], m["note"])

            if row.get("total2") is not None:
                row["total2"] = (row["total2"] or 0) + adj_total
                if row.get("formula2"):
                    for m in mods:
                        row["formula2"] = _append(row["formula2"], m["value"], m["note"])

    # ------- Handle "Save Skill Proficiencies" POST with reason required -------
    skill_prof_errors = []
    if request.method == "POST" and "save_skill_profs_submit" in request.POST and can_edit:
        to_apply = []
        for row in all_skill_rows:
            field = f"sp_{row['id_key']}"
            new_pk = request.POST.get(field)
            if not new_pk:  # None or ""
                    continue
            if new_pk is None:
                continue
            if str(new_pk) != str(row["prof_id"] or ""):
                note = (request.POST.get(f"sp_note_{row['id_key']}") or "").strip()
                if not note:
                    skill_prof_errors.append(row["label"])
                else:
                    to_apply.append((row, int(new_pk), note))

        if skill_prof_errors:
            # fall through to render; template will show which rows need a reason
            pass
        else:
            for row, new_pk, note in to_apply:
                new_prof = ProficiencyLevel.objects.get(pk=new_pk)
                if row["is_sub"]:
                    ctype = ct_sub
                    obj_id = row["sub_id"]
                else:
                    ctype = ct_skill
                    obj_id = row["skill_id"]

                rec, created = CharacterSkillProficiency.objects.get_or_create(
                    character=character,
                    selected_skill_type=ctype,
                    selected_skill_id=obj_id,
                    defaults={"proficiency": new_prof},
                )
                if not created and rec.proficiency_id != new_prof.pk:
                    rec.proficiency = new_prof
                    rec.save()




                # log reason with CharacterFieldNote for audit
                CharacterFieldNote.objects.update_or_create(
                    character=character,
                    key=f"skill_prof:{row['id_key']}",
                    defaults={"note": note},
                )
                    # --- NEW: persistent history entry (old -> new) ---
                old_name = row.get("prof_name") or "Untrained"
                new_name = (new_prof.name or "").title()
                CharacterFieldNote.objects.update_or_create(
                    character=character,
                    key=f"skill_prof_hist:{row['id_key']}:{uuid.uuid4().hex[:8]}",
                    defaults={"note": f"{old_name} → {new_name}: {note}"}
                )


            return redirect("characters:character_detail", pk=pk)



    # ---- FEATS & FEATURES (owned) ----
    owned_feats = (
        character.feats
        .select_related('feat')
        .order_by('level', 'feat__name')
    )

    general_feats = [cf for cf in owned_feats if (cf.feat.feat_type or "").strip().lower() == "general"]
    class_feats   = [cf for cf in owned_feats if (cf.feat.feat_type or "").strip().lower() == "class"]
    other_feats   = [cf for cf in owned_feats if (cf.feat.feat_type or "").strip().lower() not in ("general","class")]

    owned_features = (
        character.features
        .select_related('feature','racial_feature','subclass','option')
        .order_by('level')
    )
    # Activation state map
    acts = CharacterActivation.objects.filter(character=character)
    act_map = {(a.content_type_id, a.object_id): a.is_active for a in acts}

    ct_classfeat   = ContentType.objects.get_for_model(ClassFeat)
    ct_classfeature= ContentType.objects.get_for_model(ClassFeature)

    owned_feats = list(CharacterFeat.objects.filter(character=character).select_related("feat"))
    owned_features = list(
        CharacterFeature.objects
        .filter(character=character, feature__isnull=False)
        .select_related("feature", "feature__character_class", "subclass")
    )

    feat_rows = [{
        "ctype": ct_classfeat.id,
        "obj_id": cf.feat.id,
        "label": cf.feat.name,
        "meta":  f"Lv {cf.level}",
        "active": act_map.get((ct_classfeat.id, cf.feat.id), False),
        "note_key": f"cfeat:{cf.id}",
        "desc": (getattr(cf.feat, "description", "") or getattr(cf.feat, "summary", "") or ""),
        "details": _feat_details_map(cf.feat),   # ← add this
    } for cf in owned_feats if cf.feat_id]

    feature_rows = []
    for cfeat in owned_features:
        label = cfeat.feature.name
        meta  = []
        if cfeat.feature.character_class_id:
            meta.append(cfeat.feature.character_class.name)
        if cfeat.subclass_id:
            meta.append(cfeat.subclass.name)
        feature_rows.append({
            "ctype": ct_classfeature.id,
            "obj_id": cfeat.feature.id,
            "label": label,
            "meta":  " / ".join(m for m in meta if m) or "",
            "active": act_map.get((ct_classfeature.id, cfeat.feature.id), False),
            "note_key": f"cfeature:{cfeat.id}",
            "desc": (getattr(cfeat.feature, "description", "") or getattr(cfeat.feature, "summary", "") or ""),
            "details": _feature_details_map(cfeat.feature),  # ← add this
        })



    all_rows     = feat_rows + feature_rows
    active_rows  = [r for r in all_rows if r["active"]]
    passive_rows = [r for r in all_rows if not r["active"]]

    # ...after you compute prof_armor/prof_dodge/etc. and half_lvl...
    prof_weapon = prof_by_code.get("weapon", {"modifier": 0})["modifier"]
    dc_ability = None
    if primary_cp:
        # you said: only one; if data has 2, pick the first deterministically
        dc_ability = primary_cp.character_class.key_abilities.first()
    if dc_ability:
        abil_name = (dc_ability.name or "").lower()
        abil_mod  = _abil_mod(getattr(character, abil_name, 10))
        derived["spell_dc_main"] = 10 + abil_mod + prof_by_code.get("dc", {"modifier":0})["modifier"] + hl_if_trained("dc")
        derived["spell_dc_ability"] = abil_name.title()
    else:
        derived["spell_dc_main"] = 10 + prof_by_code.get("dc", {"modifier":0})["modifier"] + hl_if_trained("dc")
        derived["spell_dc_ability"] = "—"
    # keep what you already have that sets derived["spell_dc_main"] and derived["spell_dc_ability"]
    half_dc   = hl_if_trained("dc")
    abil_name = derived.get("spell_dc_ability") or "Ability"
    abil_mod  = _abil_mod(getattr(character, (abil_name or "").lower(), 10)) if abil_name != "—" else 0
    prof_dc   = prof_by_code.get("dc", {"modifier": 0})["modifier"]

    spell_dc_rows = [{
        "label":   f"Spell/DC ({abil_name})",
        "formula": "10 + prof + ½ level + ability mod",
        "values":  f"10 + {_fmt(prof_dc)} + {_fmt(half_dc)} + {_fmt(abil_mod)}",
        "total":   derived["spell_dc_main"],
        "calc": {
            "formula": "10 + prof + half + abil",
            "parts": [
                {"key":"base","label":"Base","value":10},
                {"key":"prof","label":"Proficiency","value":prof_dc,"note":prof_by_code.get("dc",{}).get("tier_name","")},
                {"key":"half","label":"½ level","value":half_dc},
                {"key":"abil","label":"Ability mod","value":abil_mod,"note":abil_name},
            ],
            "total": derived["spell_dc_main"],
        },
    }]

    # --- Equip pickers (Combat tab) ---
    weapons_list = list(
        Weapon.objects.all().order_by("name").values("id","name","damage","range_type")
    )
    # currently equipped (new 3-slot system)


    # keep “main/alt” convenience vars for old templates (map to 1/2)
    equipped_main = by_slot.get(1)
    equipped_alt  = by_slot.get(2)

    # ability mods for math
    str_mod = _abil_mod(character.strength)
    dex_mod = _abil_mod(character.dexterity)

    # --- Build attack lines per equipped weapon (show both choices when allowed) ---
    attacks_detailed = []
    for idx, label in [(1, "Primary"), (2, "Secondary"), (3, "Tertiary")]:
        rec = by_slot.get(idx)
        if not rec:
            continue
        w = rec.weapon

        # Resolve proficiency that applies to THIS weapon (item > group)
        w_prof = _effective_class_prof_for_item(
            character, "weapon",
            weapon_group=_weapon_group_for(w),
            weapon_item_id=w.id
        )
        half_w = half_lvl if w_prof["is_proficient"] else 0

        # Your helper already takes (prof, half) separately — pass the *effective* ones
        math_ = _weapon_math_for(w, str_mod, dex_mod, w_prof["bonus"], half_w)

        attacks_detailed.append({
            "slot": label,
            "weapon_id": w.id,
            "name": w.name,
            "damage_die": w.damage,
            "range_type": w.range_type,
            "traits": math_["traits"],
            "base": math_["base"],          # uses correct prof + ½ level if proficient
            "hit_str": math_["hit_str"],
            "hit_dex": math_["hit_dex"],
            "dmg_str": math_["dmg_str"],
            "dmg_dex": math_["dmg_dex"],
            "show_choice_hit": math_["show_choice_hit"],
            "show_choice_dmg": math_["show_choice_dmg"],
            "rule": math_["rule"],
            # optional UI hints:
            "proficiency_tier": w_prof["name"],
            "is_proficient": w_prof["is_proficient"],
        })


    # ----- LEFT CARD: finals only -----
    finals_left = [
        {"label": "Armor",       "value": derived["armor_total"]},
        {"label": "Dodge",       "value": derived["dodge_total"]},
        {"label": "Reflex",      "value": derived["reflex_total"]},
        {"label": "Fortitude",   "value": derived["fortitude_total"]},
        {"label": "Will",        "value": derived["will_total"]},
        {"label": "Weapon (base)","value": derived["weapon_base"]},
    ]
    if derived.get("spell_dcs"):
        # keep just the main one (you required one DC per class)
        finals_left.append({"label":"Spell/DC", "value": derived["spell_dcs"][0]["value"]})


    # ----- Tabs payloads -----
    # Details: placeholders now, fill later in your editor
    details_placeholders = {
        "appearance": character.backstory[:200] if character.backstory else "",
        "hooks": "",
        "notes": "",
    }
    # --- Martial Mastery entitlement (from owned martial_mastery features) ---
    def _eval_mm(expr, cp_map):
        if not expr: return 0
        try:
            ctx = {
                "level": character.level,
                "strength": character.strength, "dexterity": character.dexterity, "constitution": character.constitution,
                "intelligence": character.intelligence, "wisdom": character.wisdom, "charisma": character.charisma,
                "str_mod": _abil_mod(character.strength), "dex_mod": _abil_mod(character.dexterity),
                "con_mod": _abil_mod(character.constitution), "int_mod": _abil_mod(character.intelligence),
                "wis_mod": _abil_mod(character.wisdom), "cha_mod": _abil_mod(character.charisma),
                "floor": math.floor, "ceil": math.ceil, "min": min, "max": max, "round": round, "int": int,
            }
            ctx.update(cp_map)
            return int(eval(expr, {"__builtins__": {}}, ctx))
        except Exception:
            return 0
    def _build_spellcasting_summary(char):
        blocks = []
        for feature, cls, cls_level in _active_spell_tables(char):
            origin = (feature.spell_list or "").lower()
            slots_map = _slot_totals_by_origin_and_rank(char).get(origin, {})
            max_rank = max([r for r in range(1, 11) if (slots_map.get(r, 0) or 0) > 0] or [1])

            totals = _formula_totals(char)[origin]
            blocks.append({
                "klass": cls,                       # used as b.klass.name in template
                "list": origin,                     # shown as {{ b.list }}
                "slots": [int(slots_map.get(r, 0)) for r in range(1, max_rank+1)],
                "cantrips": int(totals["cantrips_known"] or 0),
                "known": int(totals["spells_known"] or 0),
                "prepared": int(totals["spells_prepared_cap"] or 0),
            })
        return blocks


    # Build class-level tokens like "wizard_level": 3, "fighter_level": 2
    _class_levels_ctx = {}
    for prog in class_progress:
        token = re.sub(r'[^a-z0-9_]', '', (prog.character_class.name or '').strip().lower().replace(' ', '_'))
        if token:
            _class_levels_ctx[f"{token}_level"] = prog.levels

    owned_mm_features = list(
        ClassFeature.objects.filter(
            kind="martial_mastery",
            character_features__character=character
        ).select_related("character_class").distinct()
    )

    # IMPORTANT: only build the entitlement if the character actually owns a martial_mastery feature
    martial_mastery_ctx = None
    if owned_mm_features:
        mm_entries = []
        total_mm_points = 0
        total_mm_known_cap = 0
        for ft in owned_mm_features:
            pts   = _eval_mm(getattr(ft, "martial_points_formula", None), _class_levels_ctx)
            known = _eval_mm(getattr(ft, "available_masteries_formula", None), _class_levels_ctx)
            total_mm_points    += max(0, pts)
            total_mm_known_cap += max(0, known)
            mm_entries.append({
                "feature_id": ft.id,
                "feature_name": ft.name,
                "class_name": ft.character_class.name if ft.character_class_id else "",
                "points": pts,
                "known_cap": known,
            })

        martial_mastery_ctx = {
            "total_points": total_mm_points,
            "total_known_cap": total_mm_known_cap,
            "by_feature": mm_entries,
            "known_list": [m.mastery for m in character.martial_masteries.select_related("mastery").all()]
                        if hasattr(character, "martial_masteries") else [],
        }

    # Combat tab (defense/offense split)
    combat_blocks = {
        "defense": [
            {"label":"Armor", "value": derived["armor_total"]},
            {"label":"Dodge", "value": derived["dodge_total"]},
            {"label":"Reflex","value": derived["reflex_total"]},
            {"label":"Fortitude","value": derived["fortitude_total"]},
            {"label":"Will","value": derived["will_total"]},
        ],
        "offense": {
            "spell_dc": (derived["spell_dcs"][0]["value"] if derived.get("spell_dcs") else None),
            "weapons": attacks_detailed,
        },
    }
    # Add this block only when entitlement exists
    if martial_mastery_ctx:
        combat_blocks["martial_mastery"] = {
            "total_points": martial_mastery_ctx["total_points"],
            "total_known_cap": martial_mastery_ctx["total_known_cap"],
            "known_names": [getattr(k, "name", str(k)) for k in martial_mastery_ctx["known_list"]],
        }



    # Feats tab (you already compute these)
    feats_tab = {
        "general": general_feats,
        "class":   class_feats,
        "other":   other_feats,
    }

    # Active/Passive tab:
    # — features with “Active” trait (activity_type == 'active' in your model)
    active_candidates = list(ClassFeature.objects
                             .filter(character_features__character=character,
                                     activity_type="active")
                             .distinct())
    passive_candidates = list(ClassFeature.objects
                              .filter(character_features__character=character,
                                      activity_type="passive")
                              .distinct())

    # — spells (known + prepared) summarized against your spell slot tables
    spell_tables = spellcasting_blocks  # you already build this earlier
    known_spells = list(character.known_spells.select_related("spell").all())
    prepared_spells = list(character.prepared_spells.select_related("spell").all())
    prepared_spell_rows = []
    for ps in prepared_spells:  # you already have: list(character.prepared_spells.select_related("spell").all())
        sp = ps.spell
        prepared_spell_rows.append({
            "name": sp.name,
            "origin": (ps.origin or (sp.origin or "")).strip().title(),
            "rank": int(ps.rank or getattr(sp, "level", 0) or 0),
            "classification": getattr(sp, "classification", "") or "",
            "tags": getattr(sp, "tags", "") or "",
            "casting_time": getattr(sp, "casting_time", "") or "",
            "duration": getattr(sp, "duration", "") or "",
            "components": getattr(sp, "components", "") or "",
            "range": getattr(sp, "range", "") or "",
            "target": getattr(sp, "target", "") or "",
            "saving_throw": getattr(sp, "saving_throw", "") or "",
            "effect": getattr(sp, "effect", "") or "",
            "upcast_effect": getattr(sp, "upcast_effect", "") or "",
        })
    prepared_spell_rows.sort(key=lambda r: (r["rank"], r["name"].lower()))
        # — martial masteries
    masteries = list(character.martial_masteries.select_related("mastery").all())

    # — current activation states + notes
    activations_map = {
        (a.content_type_id, a.object_id): {"active": a.is_active, "note": a.note}
        for a in character.activations.all()
    }

    active_passive_tab = {
        "features_active":   active_candidates,
        "features_passive":  passive_candidates,
        "spell_tables":      spell_tables,
        "known_spells":      known_spells,
        "prepared_spells":   prepared_spells,
        "masteries":         masteries,
        "activations_map":   activations_map,
        "actions_text": True,
    }
    # Attach only if present
    if martial_mastery_ctx:
        active_passive_tab["martial_mastery_entitlement"] = martial_mastery_ctx

    # Build combined flat list for checkboxes (labels sorted A→Z)
    starting_skill_flat = []
    for s in starting_skill_choices.get("skills", []):
        starting_skill_flat.append({"id_key": f"sk_{s['id']}", "label": s["label"]})
    for s in starting_skill_choices.get("subskills", []):
        starting_skill_flat.append({"id_key": f"sub_{s['id']}", "label": s["label"]})
    starting_skill_flat.sort(key=lambda x: (x["label"] or "").lower())

    # ----- include in context -----
    extra_ctx = {
        "finals_left": finals_left,
        "weapons_list": weapons_list,
        "equipped_weapon_1": by_slot.get(1).weapon if by_slot.get(1) else None,
        "equipped_weapon_2": by_slot.get(2).weapon if by_slot.get(2) else None,
        "equipped_weapon_3": by_slot.get(3).weapon if by_slot.get(3) else None,
        "attacks_detailed": attacks_detailed,
        "details_placeholders": details_placeholders,
        "combat_blocks": combat_blocks,
        "feats_tab": feats_tab,
        "active_passive_tab": active_passive_tab,
    }

    context_updates = {
        'weapons_list': weapons_list,
        'equipped_weapon_main': equipped_main.weapon if equipped_main else None,
        'equipped_weapon_alt':  equipped_alt.weapon  if equipped_alt  else None,
        'attacks_detailed': attacks_detailed,
        'spell_dc_main': derived.get("spell_dc_main"),
        'spell_dc_ability': derived.get("spell_dc_ability"),
    }
    # include in your final render(...) call:
    # ---- Final aliases for context (fix NameErrors) ----
    rows = defense_rows
    spell_dc_main = derived.get("spell_dc_main")
    # === Spell table data (Known + Prepared counts), grouped by rank ===
    # === Spell table data (Known + Prepared counts), grouped by rank ===
    scx = _spellcasting_context(character)
    rows_by_rank = {r: [] for r in scx["rank_range"]}

    # Prepared counts per (origin, rank)
    prep = scx["prepared_counts"]  # e.g. {'arcane': {1: 2, 2: 1}, ...}

    # Known spells (use the spell's own origin; CharacterKnownSpell may not store origin)
    for ks in character.known_spells.select_related("spell").all():
        sp = ks.spell
        origin_code = (getattr(sp, "origin", "") or "").strip().lower()
        rank = int(getattr(ks, "rank", getattr(sp, "level", 0)) or 0)
        prepared_count = int(prep.get(origin_code, {}).get(rank, 0))

        rows_by_rank.setdefault(rank, []).append({
            "name":           sp.name,
            "origin":         origin_code,
            "rank":           rank,
            "classification": getattr(sp, "classification", "") or "",
            "tags":           getattr(sp, "tags", "") or "",
            "prepared_count": prepared_count,
        })

    # Helper list for the template (avoids dict indexing hassles)
    spell_rank_blocks = [{"rank": r, "rows": rows_by_rank.get(r, [])} for r in scx["rank_range"]]

    show_spellcasting_tab = is_spellcaster or bool(spell_selection_blocks)
    # --- Manual caps adjustment (with reason) ------------------------------------
    if request.method == "POST" and request.POST.get("spells_op") == "adjust_caps" and can_edit:
        fid = int(request.POST.get("feature_id") or 0)
        note = (request.POST.get("note") or "").strip()
        if not note:
            messages.error(request, "Reason is required.")
            return redirect('characters:character_detail', pk=pk)

        def _save_cap(key, form_key):
            raw = (request.POST.get(form_key) or "").strip()
            if raw == "":
                return
            try: val = int(raw)
            except ValueError:
                messages.error(request, f"{form_key} must be a number.")
                raise
            CharacterFieldOverride.objects.update_or_create(
                character=character, key=f"spellcap:{fid}:{key}", defaults={"value": str(val)}
            )
            CharacterFieldNote.objects.update_or_create(
                character=character, key=f"spellcap:{fid}:{key}", defaults={"note": note}
            )

        try:
            _save_cap("cantrips", "cap_cantrips")
            _save_cap("known",    "cap_known")
            _save_cap("prepared", "cap_prepared")
        except Exception:
            return redirect('characters:character_detail', pk=pk)
        return redirect('characters:character_detail', pk=pk)

    # --- Learn / Unlearn / Prepare / Unprepare -----------------------------------
    # ── Spell learn/prepare ops (table-driven; supports bulk via pick[]) ───────────


# ...

    if request.method == "POST" and request.POST.get("spells_op") in {
        "prepare","unprepare","learn_known","learn_cantrip","unlearn_known","unlearn_cantrip"
    }:
        if not can_edit:
            return HttpResponseBadRequest("Not allowed.")

        op   = request.POST.get("spells_op")
        fid  = int(request.POST.get("feature_id") or 0)
        picks = request.POST.getlist("pick[]")  # values from the table
        blk = next((b for b in spell_selection_blocks if int(b["feature_id"]) == fid), None)
        if not blk:
            messages.error(request, "Invalid spell table selection.")
            return redirect('characters:character_detail', pk=pk)

        if op == "learn_cantrip":
            remaining = max(0, int(blk["cantrips_max"]) - int(blk["known_cantrips_current"]))
            if remaining <= 0:
                messages.error(request, "No cantrip slots remaining.")
                return redirect('characters:character_detail', pk=pk)
            if len(picks) > remaining:
                messages.error(request, f"Selected {len(picks)} cantrips, but only {remaining} slot(s) remain.")
                return redirect('characters:character_detail', pk=pk)

        elif op == "learn_known":
            if blk["known_max"] is None:
                messages.error(request, "This casting style doesn’t use a known-spells cap.")
                return redirect('characters:character_detail', pk=pk)
            remaining = max(0, int(blk["known_max"]) - int(blk["known_leveled_current"]))
            if remaining <= 0:
                messages.error(request, "No leveled spell slots remaining to learn.")
                return redirect('characters:character_detail', pk=pk)
            if len(picks) > remaining:
                messages.error(request, f"Selected {len(picks)} spells, but only {remaining} slot(s) remain.")
                return redirect('characters:character_detail', pk=pk)

        elif op == "prepare":
            # picks look like "spell_id|rank" – enforce per-rank remaining
            by_rank = {}
            for val in picks:
                sid, rk = (val.split("|", 1) + ["", ""])[:2]
                r = int(rk or 0)
                by_rank[r] = by_rank.get(r, 0) + 1
            for r, cnt in by_rank.items():
                left = int(blk["prepared_remaining_by_rank"].get(r, 0))
                if left <= 0:
                    messages.error(request, f"No preparation slots left at rank {r}.")
                    return redirect('characters:character_detail', pk=pk)
                if cnt > left:
                    messages.error(request, f"Selected {cnt} spell(s) at rank {r}, but only {left} slot(s) remain.")
                    return redirect('characters:character_detail', pk=pk)
        # unprepare/unlearn need no caps

        if not picks:
            messages.error(request, "Select at least one spell.")
            return redirect('characters:character_detail', pk=pk)

        ft = get_object_or_404(ClassFeature, pk=fid, kind="spell_table")
        origin_label = (getattr(ft, "get_spell_list_display", lambda: None)() or ft.spell_list or "").strip()

        def _okey(v: str) -> str:
            v = (v or "").strip().lower()
            return v or "—"

        origin_key = _okey(origin_label)

        Known    = character.known_spells.model
        Prepared = character.prepared_spells.model

        starting_skill_max = 0

        try:
            with transaction.atomic():
                if op == "learn_cantrip":
                    for val in picks:  # "spell_id|0" or sometimes just "spell_id"
                        sid, rk = (val.split("|", 1) + ["", ""])[:2]
                        sid_i = int(sid)
                        # cantrip rank is always 0
                        Known.objects.update_or_create(
                            character=character,
                            spell_id=sid_i,
                            defaults={"origin": origin_key, "rank": 0},
                        )

                elif op == "learn_known":
                    for val in picks:  # "spell_id|rank" (rank is required, but recover if omitted)
                        sid, rk = (val.split("|", 1) + ["", ""])[:2]
                        sid_i = int(sid)
                        # if UI didn't include rank, fall back to the Spell.level
                        if rk == "":
                            rk = Spell.objects.filter(pk=sid_i).values_list("level", flat=True).first() or 0
                        rk_i = int(rk)
                        # learn_known
                        Known.objects.update_or_create(
                            character=character,
                            spell_id=sid_i,
                            defaults={"origin": origin_key, "rank": rk_i},
                        )



                elif op == "unlearn_cantrip" or op == "unlearn_known":
                    for kid in picks:     # values are Known rows' ids
                        Known.objects.filter(character=character, id=int(kid)).delete()

                elif op == "prepare":
                    for val in picks:     # "spell_id|rank"
                        sid, rk = (val.split("|", 1) + ["", ""])[:2]
                        Prepared.objects.get_or_create(
                            character=character, spell_id=int(sid), rank=int(rk or 0),
                            defaults={"origin": origin_key}
                        )

                elif op == "unprepare":
                    for pid in picks:     # values are Prepared rows' ids
                        Prepared.objects.filter(character=character, id=int(pid)).delete()

        except Exception as e:
            # Keep this simple; if you want, log e for diagnostics.
            messages.error(request, "Could not update spells.")
            return redirect('characters:character_detail', pk=pk)

        return redirect('characters:character_detail', pk=pk)


    skill_points_balance = CharacterSkillPointTx.balance_for(character)

    # ── 6) RENDER character_detail.html ───────────────────────────────────
    return render(request, 'forge/character_detail.html', {
        "spell_table_by_rank": rows_by_rank,
        "show_starting_skill_picker": show_starting_skill_picker,
"starting_skill_choices": starting_skill_choices,
        "spell_rank_range": scx["rank_range"],
        "spellcasting_ctx": _spellcasting_context(character),
        'character':          character,
        "show_spellcasting_tab": show_spellcasting_tab,
        'can_edit':           can_edit,
        'subrace_name':       subrace_name,
        'subclass_groups': subclass_groups,
        'ability_map':        ability_map,
        'skill_proficiencies':skill_proficiencies,
        'class_progress':     class_progress,
        'racial_features':    racial_features,
        'universal_feats':    universal_feats,
        'total_level':        total_level,
        'preview_class':      preview_cls,
        'tier_names':         tier_names,
        "starting_skill_max": starting_skill_max,
        'auto_feats':         auto_feats,
        'form':               level_form,
        'edit_form':          edit_form,
        'details_form':       details_form,
    'feature_fields':         feature_fields,
    'spellcasting_blocks': spellcasting_blocks,
    "skill_points_balance": skill_points_balance,

    'subclass_feats_at_next': subclass_feats_at_next,
            'proficiency_rows':   proficiency_rows,   # (preview table you already had)
        'proficiency_summary': proficiency_summary,
        'racial_feature_rows': racial_feature_rows,
        'manual_form': manual_form,
        "starting_skill_flat": starting_skill_flat,

        'manual_grants': character.manual_grants.select_related('content_type').all(),
            'field_overrides': field_overrides,
            'field_notes': field_notes,
        'derived':            derived,
        'skills_rows':        all_skill_rows,
        'proficiency_levels': prof_levels,
        'skill_prof_errors':  skill_prof_errors,
        'general_feats': general_feats,
'class_feats':   class_feats,
'other_feats':   other_feats,
'owned_features': owned_features,
'armor_list': armor_list,
'selected_armor': selected_armor,
       'spellcasting_blocks': spellcasting_blocks,   # you already pass this
        'spell_selection_blocks': spell_selection_blocks,  # NEW
'proficiency_detailed': rows,
'attack_rows': attack_rows,
'spell_dc_rows': spell_dc_rows,
    'ability_map': ability_map,
    'abilities': abilities, 
'armor_total': derived["armor_total"],
'spell_dc_rows': spell_dc_rows,
'attack_rows': attack_rows,
    "derived": derived,
    "armor_total": derived["armor_total"],  # keep legacy var if the template uses it elsewhere
    "attack_rows": attack_rows,
    "spell_dc_rows": spell_dc_rows,
    "spell_dc_main": spell_dc_main,
    "defense_rows": defense_rows,
    "hp_current": hp_current,
    "hp_max": hp_max,
    "temp_hp": temp_hp,
    "active_rows": active_rows,
    "passive_rows": passive_rows,
    "all_rows": all_rows,
    # if you also reference selected_armor/armor_list anywhere:
    "armor_list": armor_list,
    "selected_armor": selected_armor,
    "spell_rank_blocks": spell_rank_blocks,



    })


# NEW — dedicated view for applying a level-up
@login_required
def character_level_up(request, pk):
    """
    Handles ONLY the level-up POST flow, then redirects back to character_detail.
    HTML stays the same: forms still post to 'characters:character_detail';
    character_detail() will delegate here when it sees 'level_up_submit' in POST.
    """
    if request.method != "POST" or "level_up_submit" not in request.POST:
        return redirect('characters:character_detail', pk=pk)

    # ── (A) Copy the SAME permission logic from character_detail ─────────────
    # PASTE: from character_detail — the block that loads `character`, computes
    # is_gm_for_campaign, enforces permission, and sets `can_edit`.
    character = get_object_or_404(Character, pk=pk)
    is_gm_for_campaign = False
    if character.campaign_id:
        is_gm_for_campaign = CampaignMembership.objects.filter(
            campaign=character.campaign, user=request.user, role="gm"
        ).exists()
    if not (request.user.id == character.user_id or is_gm_for_campaign):
        return HttpResponseForbidden("You don’t have permission to view this character.")
    can_edit = (request.user.id == character.user_id) or is_gm_for_campaign
    if not can_edit:
        return HttpResponseForbidden("Not allowed.")

    # ── (B) Local helpers needed by the POST branch (copy verbatim) ──────────
    # PASTE the THREE helper defs from character_detail that the level-up POST uses:
    def _starting_skills_cap_for(cls_obj):
        expr = (getattr(cls_obj, "starting_skills_formula", "") or "").strip()
        if not expr:
            return 0

        def _abil(score: int) -> int:
            return (score - 10) // 2

        # IMPORTANT: short names -> MODIFIERS
        ctx = {
            # modifiers (primary names)
            "strength": _abil(character.strength), "dexterity": _abil(character.dexterity),
            "constitution": _abil(character.constitution), "intelligence": _abil(character.intelligence),
            "wisdom": _abil(character.wisdom), "charisma": _abil(character.charisma),

            # explicit *_mod aliases (same values as above)
            "str_mod": _abil(character.strength), "dex_mod": _abil(character.dexterity),
            "con_mod": _abil(character.constitution), "int_mod": _abil(character.intelligence),
            "wis_mod": _abil(character.wisdom), "cha_mod": _abil(character.charisma),

            # scores (only if you want them available explicitly)
            "strength_score": character.strength, "dexterity_score": character.dexterity,
            "constitution_score": character.constitution, "intelligence_score": character.intelligence,
            "wisdom_score": character.wisdom, "charisma_score": character.charisma,

            # math/helpers
            "floor": math.floor, "ceil": math.ceil, "min": min, "max": max,
            "int": int, "round": round,
        }

        # <class>_level tokens (wizard_level, fighter_level, ...)
        for prog in character.class_progress.select_related('character_class'):
            token = re.sub(r'[^a-z0-9_]', '', (prog.character_class.name or '')
                        .strip().lower().replace(' ', '_'))
            if token:
                ctx[f"{token}_level"] = int(prog.levels or 0)

        try:
            val = eval(_normalize_formula(expr), {"__builtins__": {}}, ctx)
            return max(0, int(val))
        except Exception:
            return 0
    def _active_subclass_for_group(character, grp, level_form=None, base_feats=None):
        """
        Returns the chosen Subclass for `grp` using (in order):
        1) the POSTed choice this request (if present),
        2) the last saved 'subclass_choice' CharacterFeature,
        3) the last saved 'subclass_feat' (infers subclass),
        4) an explicit override 'subclass_choice:<grp.id>' if you use that,
        else None.
        """
        # 0) if this request posts a subclass choice field, use it
        if level_form is not None and getattr(level_form, "is_bound", False):
            base_feats = list(base_feats or [])
            sc_choices = [
                f for f in base_feats
                if isinstance(f, ClassFeature)
                and getattr(f, "scope", "") == "subclass_choice"
                and getattr(f, "subclass_group_id", None) == grp.id
            ]
            for f in sc_choices:
                key = f"feat_{f.pk}_subclass"
                raw = (level_form.data.get(key) or "").strip()
                if raw.isdigit():
                    try:
                        return grp.subclasses.get(pk=int(raw))
                    except grp.subclasses.model.DoesNotExist:
                        pass

        # 1) last explicitly saved subclass choice
        row = (CharacterFeature.objects
            .filter(character=character,
                    feature__scope="subclass_choice",
                    feature__subclass_group=grp)
            .exclude(subclass__isnull=True)
            .order_by("-level", "-id")
            .first())
        if row and row.subclass_id:
            return row.subclass

        # 2) infer from owned subclass features
        row = (CharacterFeature.objects
            .filter(character=character,
                    feature__scope="subclass_feat",
                    feature__subclass_group=grp)
            .exclude(subclass__isnull=True)
            .order_by("-level", "-id")
            .first())
        if row and row.subclass_id:
            return row.subclass

        # 3) optional manual override
        ov = CharacterFieldOverride.objects.filter(character=character, key=f"subclass_choice:{grp.id}").first()
        if ov and str(ov.value).strip().isdigit():
            try:
                return grp.subclasses.get(pk=int(ov.value))
            except grp.subclasses.model.DoesNotExist:
                pass

        return None
    def _linear_feats_for_level(cls_obj, grp, subclass, cls_level, base_feats=None):

        if not subclass:
            return []

        feats = []
        for f in (base_feats or []):
            if (getattr(f, "scope", "") == "subclass_feat"
                and getattr(f, "subclass_group_id", None) == grp.id
                and (subclass in f.subclasses.all())):
                lr = getattr(f, "level_required", None)
                ml = getattr(f, "min_level", None)
                if (ml is None or int(ml) <= int(cls_level)) and (lr is None or int(lr) <= int(cls_level)):
                    feats.append(f)

        if feats:
            return feats

        # Fallback: only when nothing is attached to this level (avoid leaking ungated L1 features)
        return list(
            ClassFeature.objects
                .filter(scope="subclass_feat", subclass_group=grp, subclasses=subclass)
                .filter(
                    Q(level_required=cls_level) |
                    Q(level_required__isnull=True, min_level__lte=cls_level)
                )
                .exclude(level_required__isnull=True, min_level__isnull=True)
        )
    #
    # (Keep their bodies exactly the same as in your current function.)



    # ── (C) Recreate the same context the POST branch assumes ───────────────
    class_progress = character.class_progress.select_related('character_class')
    total_level = character.level
    next_level = total_level + 1
    first_prog = class_progress.first()
    default_cls = first_prog.character_class if first_prog else CharacterClass.objects.order_by("name").first()

    posted_cls_id = request.POST.get('base_class')
    try:
        posted_cls = CharacterClass.objects.get(pk=int(posted_cls_id))
    except (TypeError, ValueError, CharacterClass.DoesNotExist):
        posted_cls = default_cls

    cls_level_for_validate = _class_level_after_pick(character, posted_cls)

    # features used at THIS (class, level)
    try:
        cl_validate = (
            ClassLevel.objects
            .prefetch_related(
                'features__subclasses',
                'features__subclass_group',
                'features__options__grants_feature',
            )
            .get(character_class=posted_cls, level=cls_level_for_validate)
        )
        base_feats = list(cl_validate.features.all())
    except ClassLevel.DoesNotExist:
        base_feats = []

    # only real ClassFeature instances go here
    to_choose = base_feats.copy()

    # same boolean you computed in character_detail
    _grants_class_feat_at = any(
        isinstance(f, ClassFeature) and (
            (getattr(f, "scope", "") in ("class_feat_pick", "class_feat_choice"))
            or ("class feat" in (f.name or "").strip().lower())
            or ("class_feat" in ((getattr(f, "code", "") or "").strip().lower()))
            or ((getattr(f, "kind", "") or "").strip().lower()
                in ("class_feat_pick", "class_feat_choice", "grant_class_feat"))
        )
        for f in base_feats
    )

    uni = UniversalLevelFeature.objects.filter(level=next_level).first()
    target_cls = posted_cls
    cls_after  = cls_level_for_validate
    cls_name   = target_cls.name

    # ── (D) Build LevelUpForm with the exact same options/fields ────────────
    level_form = LevelUpForm(
        request.POST,
        character=character,
        to_choose=to_choose,
        uni=uni,
        preview_cls=posted_cls,              # ok to pass posted class here
        grants_class_feat=_grants_class_feat_at
    )

    # Conditional dynamic fields — COPY EXACTLY your logic:
    #   - add "class_feat_pick" when needed
    if _grants_class_feat_at and "class_feat_pick" not in level_form.fields:
        level_form.fields["class_feat_pick"] = forms.ModelChoiceField(
            queryset=ClassFeat.objects.all(),
            required=True,
            label="Class Feat"
        )

    #   - add "skill_feat_pick" (single or multiple) when ClassSkillFeatGrant exists
    skill_grant = (
        ClassSkillFeatGrant.objects
        .filter(character_class=posted_cls, at_level=cls_level_for_validate)
        .first()
    )
    if skill_grant and "skill_feat_pick" not in level_form.fields:
        picks = int(skill_grant.num_picks or 0)
        base_qs = ClassFeat.objects.all()  # will be filtered to feat_type='Skill' below
        if picks <= 1:
            level_form.fields["skill_feat_pick"] = forms.ModelChoiceField(
                queryset=base_qs,
                required=(picks > 0),
                label="Skill Feat",
                help_text=(None if picks > 0 else "No skill-feat pick at this level.")
            )
        else:
            level_form.fields["skill_feat_pick"] = forms.ModelMultipleChoiceField(
                queryset=base_qs,
                required=(picks > 0),
                label=f"Pick {picks} Skill Feat(s)",
                widget=forms.CheckboxSelectMultiple
            )


    # ── (E) RECREATE the same subclass/trigger dynamic fields ───────────────
    # COPY the WHOLE block that builds `feature_fields` in character_detail,
    # starting at:
    feature_fields = []

    gain_sub_feat_triggers = [
        f for f in to_choose
        if isinstance(f, ClassFeature) and f.scope == 'gain_subclass_feat'
    ]

    #   def _active_subclass_for_group(...):
    #   def _linear_feats_for_level(...):

    for trigger in gain_sub_feat_triggers:
        grp = trigger.subclass_group
        if not grp:
            continue

        field_name = f"feat_{trigger.pk}_subfeats"


        active_sub = None  # only relevant for LINEAR or MASTERY

        # ---------------- LINEAR ----------------
        if grp.system_type == SubclassGroup.SYSTEM_LINEAR:
            active_sub = _active_subclass_for_group(character, grp, level_form, base_feats)
            feats_now = _linear_feats_for_level(posted_cls, grp, active_sub, cls_level_for_validate, base_feats)

            # Display-only: these subclass features will be auto-granted on submit
            feature_fields.append({
                "kind": "gain_subclass_feat",
                "label": f"Gain Subclass Feature – {grp.name}",
                "field": None,                  # read-only; no pick for LINEAR
                "group": grp,
                "subclass": active_sub,
                "eligible": list(feats_now),
                "system": grp.system_type,
            })
            continue



        # ------------- MODULAR LINEAR -------------
        if grp.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
            # tiers unlocking right now
            # tiers available up to (and including) this class level
            unlock_tiers = _unlocked_tiers(grp, cls_level_for_validate)



            # everything this character already took in THIS group
            taken_rows = (CharacterFeature.objects
                        .filter(character=character,
                                feature__scope='subclass_feat',
                                feature__subclass_group=grp)
                        .values_list('feature_id', 'subclass_id', 'feature__tier'))
            taken_feature_ids = {fid for (fid, _sid, _tier) in taken_rows}
            prev_tiers_by_sub = {}
            for (_fid, sid, tier) in taken_rows:
                if tier is None:
                    continue
                prev_tiers_by_sub.setdefault(sid, set()).add(tier)
            # union of eligible features across ALL subclasses in this group
            eligible_ids = []
            # union of eligible features across ALL subclasses in this group
            for sub in grp.subclasses.all():
                base = (
                    ClassFeature.objects
                    .filter(scope='subclass_feat', subclasses=sub)
                    .filter(Q(subclass_group=grp) | Q(subclasses__group=grp))
                    .filter(tier__in=unlock_tiers)
                    .filter(Q(level_required__isnull=True) | Q(level_required__lte=cls_level_for_validate))
                    .filter(Q(min_level__isnull=True)      | Q(min_level__lte=cls_level_for_validate))
                    .exclude(pk__in=taken_feature_ids)
                )



                for f in base:
                    if f.tier == 1 or ((f.tier - 1) in prev_tiers_by_sub.get(sub.pk, set())):
                        eligible_ids.append(f.pk)


            eligible_qs = ClassFeature.objects.filter(pk__in=eligible_ids).order_by('name')



            # required only if there is anything to pick this level
            level_form.fields[field_name] = forms.ModelMultipleChoiceField(
                label=f"Pick {grp.name} feature(s)",
                queryset=eligible_qs,
                required=bool(eligible_ids),
                widget=forms.CheckboxSelectMultiple
            )

            feature_fields.append({
                "kind": "gain_subclass_feat",
                "label": f"Gain Subclass Feature – {grp.name}",
                "field": level_form[field_name],
                "group": grp,
                "subclass": None,          # not tied to one subclass in modular-linear
                "eligible": list(eligible_qs),
                "system": grp.system_type,
            })
            continue

        # ------------- MODULAR MASTERY (TRIGGER-DRIVEN) -------------
        if grp.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
            from django.db.models import Count

            field_name = f"feat_{trigger.pk}_subfeats"

            # how many modules per tier (default 2 if not set)
            per = max(1, int(getattr(grp, "modules_per_mastery", 2)))

            # how many picks this trigger gives (usually 1)
            picks_per_trigger = _picks_for_trigger(trigger, posted_cls, cls_level_for_validate)


            # the *gainer’s* cap for tier you may pick up to (None/0 = unlimited)
            gainer_cap = int(getattr(trigger, "mastery_rank", 0) or 0)  # 0/None => unbounded

            # what we’ve already taken (per subclass) for this group
            taken_by_sub = dict(
                CharacterFeature.objects.filter(
                    character=character,
                    feature__scope='subclass_feat',
                    feature__subclass_group=grp
                ).values('subclass_id').annotate(cnt=Count('id'))
                .values_list('subclass_id', 'cnt')
            )

            # current tier per subclass (start at tier 1; advance every 'per' modules)
            current_tier_by_sub = {}
            for sub in grp.subclasses.all():
                taken = int(taken_by_sub.get(sub.id, 0))
                current_tier_by_sub[sub.id] = 1 + (taken // per)

            # feature ids already owned in this group (avoid duplicates)
            owned_feat_ids = set(
                CharacterFeature.objects.filter(
                    character=character, feature__scope='subclass_feat',
                    feature__subclass_group=grp
                ).values_list('feature_id', flat=True)
            )

            # build eligible set across *all* subclasses
            eligible_ids = []
            for sub in grp.subclasses.all():
                # allowed tier for this subclass this time:
                # <= current tier, and <= trigger's cap if it exists
                allowed_cap = current_tier_by_sub[sub.id]
                if gainer_cap:
                    allowed_cap = min(allowed_cap, gainer_cap)

                q = ClassFeature.objects.filter(
                    scope='subclass_feat',
                    subclasses=sub
                ).filter(
                    Q(subclass_group=grp) | Q(subclasses__group=grp)
                )

                if allowed_cap:
                    q = q.filter(models.Q(mastery_rank__isnull=True) |
                                models.Q(mastery_rank__lte=allowed_cap))

                # NO level attachments — do not filter by ClassLevel; optionally keep min_level if you use it
                q = q.exclude(pk__in=owned_feat_ids)

                eligible_ids.extend(q.values_list('id', flat=True))

            eligible_qs = ClassFeature.objects.filter(pk__in=eligible_ids) \
                .order_by('mastery_rank', 'name')

            help_txt = (
                f"Pick exactly {picks_per_trigger} module"
                f"{'' if picks_per_trigger == 1 else 's'}. You can pick from any subclass. "
                f"Tiers per subclass now: "
                + ", ".join(
                    f"{s.name}≤{current_tier_by_sub.get(s.id,1)}"
                    + (f" (cap {gainer_cap})" if gainer_cap else "")
                    for s in grp.subclasses.all()
                )
            )

            # ALWAYS create the field (prevents KeyError on POST)
            level_form.fields[field_name] = forms.ModelMultipleChoiceField(
                label=f"Pick {grp.name} feature(s)",
                queryset=eligible_qs,
                required=(picks_per_trigger > 0),
                widget=forms.CheckboxSelectMultiple,
                help_text=help_txt,
            )

            feature_fields.append({
                "kind": "gain_subclass_feat",
                "label": f"Gain Subclass Feature – {grp.name}",
                "field": level_form[field_name],
                "group": grp,
                "subclass": None,   # no subclass choice in this system
                "eligible": list(eligible_qs),
                "system": grp.system_type,
                "mastery_meta": {
                    "picks_per_trigger": picks_per_trigger,
                    "modules_per_mastery": per,
                    "gainer_cap": gainer_cap or None,
                },
            })
            continue

    # and including the SYSTEM_MODULAR_LINEAR and SYSTEM_MODULAR_MASTERY branches
    # that add `level_form.fields[field_name] = ...`
    #
    # (Do NOT copy any rendering-only preview bits; only the parts that add fields.)
    #
    # After pasting, those fields will exist on level_form for validation below.

    # ── (F) Apply the SAME queryset restrictions you do in character_detail ─
    # COPY the three filtering blocks EXACTLY (they only touch level_form fields):
# Build race/subrace filter (identical to character_detail)
    race_names = []
    if character.race and getattr(character.race, "name", None):
        race_names.append(character.race.name)
    if character.subrace and getattr(character.subrace, "name", None):
        race_names.append(character.subrace.name)

    race_q = Q(race__exact="") | Q(race__isnull=True)
    if race_names:
        token_regexes = [rf'(^|[,;/\s]){re.escape(n)}([,;/\s]|$)' for n in race_names]
        race_token_re = "(" + ")|(".join(token_regexes) + ")"
        race_q |= Q(race__iregex=race_token_re)

    # C) GENERAL feats – only feat_type=General + race filter
    if "general_feat" in level_form.fields:
        gf_qs = level_form.fields["general_feat"].queryset
        if gf_qs is not None:
            level_form.fields["general_feat"].queryset = (
                gf_qs.filter(feat_type__iexact="General")
                    .filter(race_q)
                    .order_by("name")
            )

    if "class_feat_pick" in level_form.fields:
        # Use the same target class/level we validated with
        target_cls = posted_cls
        cls_after  = cls_level_for_validate
        cls_name   = target_cls.name


        class_tags = [t.lower() for t in target_cls.tags.values_list("name", flat=True)]
        tokens = [cls_name] + class_tags
        if "spellcaster" in class_tags:
            tokens += ["spellcaster", "spellcasting", "caster"]
        if "martial" in class_tags:
            tokens += ["martial"]

        token_res = [rf'(^|[,;/\s]){re.escape(tok)}([,;/\s]|$)' for tok in tokens if tok]
        any_token_re = "(" + ")|(".join(token_res) + ")" if token_res else None

        base = ClassFeat.objects.filter(feat_type__iexact="Class")
        membership_q = (
            Q(class_name__iregex=any_token_re) |
            Q(tags__iregex=any_token_re) |
            Q(class_name__regex=r'(?i)\b(all|any)\s+classes?\b') |
            Q(class_name__exact="") | Q(class_name__isnull=True)
        ) if any_token_re else (
            Q(class_name__regex=r'(?i)\b(all|any)\s+classes?\b') |
            Q(class_name__exact="") | Q(class_name__isnull=True)
        )

        qs = base.filter(membership_q)

        eligible_ids = [
            f.pk for f in qs
            if parse_req_level(getattr(f, "level_prerequisite", "")) <= cls_after
        ]
        if not eligible_ids:
            cls_re = rf'(^|[,;/\s]){re.escape(cls_name)}([,;/\s]|$)'
            relaxed = base.filter(
                Q(class_name__iregex=cls_re) |
                Q(class_name__regex=r'(?i)\b(all|any)\s+classes?\b') |
                Q(class_name__exact="") | Q(class_name__isnull=True)
            )
            eligible_ids = [
                f.pk for f in relaxed
                if parse_req_level(getattr(f, "level_prerequisite", "")) <= cls_after
            ]

        level_form.fields["class_feat_pick"].queryset = (
            ClassFeat.objects.filter(pk__in=eligible_ids).order_by("name")
        )


    # E) SKILL feats (if/when you add a field) – only feat_type=Skill + race filter
    if "skill_feat_pick" in level_form.fields:
        sf_qs = level_form.fields["skill_feat_pick"].queryset
        if sf_qs is not None:
            level_form.fields["skill_feat_pick"].queryset = (
                sf_qs.filter(feat_type__iexact="Skill")
                    .filter(race_q)
                    .order_by("name")
            )

    #
    # (Paste your current code for those three sections here, replacing
    #  target_cls/preview_cls with posted_cls where appropriate.)

    # ── (G) Validate; on failure mirror your old error path ──────────────────
    if not level_form.is_valid():
        # Build a friendly, specific error list and keep the modal open
        label_by_name = {}

        # Labels for “normal” fields on the form
        for b in level_form:  # bound fields
            try:
                label_by_name[b.name] = b.label or b.name
            except Exception:
                pass

        # Labels for dynamically-added subclass fields
        for item in feature_fields:
            if item.get("field"):
                try:
                    label_by_name[item["field"].name] = item.get("label") or item["field"].label or item["field"].name
                except Exception:
                    pass

        lines = []
        for fname, errs in level_form.errors.items():
            label = label_by_name.get(fname, fname)
            lines.append(f"• <strong>{label}</strong>: {'; '.join(errs)}")

        if lines:
            messages.error(request, mark_safe("Level up couldn’t be applied.<br>" + "<br>".join(lines)))
        else:
            messages.error(request, "Level up couldn’t be applied. Please fix the highlighted fields.")

        url = reverse('characters:character_detail', kwargs={"pk": pk}) + "#levelUpModal"
        return redirect(url)


    # ── (H) APPLY the level-up (copy the original body verbatim) ────────────
    # COPY EVERYTHING that was inside:

    if request.method == 'POST' and 'level_up_submit' in request.POST and level_form.is_valid():
        # ... your existing POST handler ...

        # A) update ClassProgress
        picked_cls = level_form.cleaned_data['base_class']
        cp, _ = CharacterClassProgress.objects.get_or_create(
            character=character,
            character_class=picked_cls,
            defaults={'levels': 0}
        )
        cp.levels += 1
        cp.save()
        # class level in the picked class after this level-up
        cls_level_after_post = cp.levels

        # B) bump character level
        character.level = next_level
        character.save()

        # C) (re)compute and grant auto feats for the actually picked class
        try:
            cl_next = (ClassLevel.objects
        .prefetch_related('features')
        .get(character_class=picked_cls, level=cls_level_after_post)
)


            auto_feats_post = [
                f for f in cl_next.features.all()
                if (getattr(f, "scope", "") == "class_feat" or getattr(f, "kind", "") == "spell_table")
            ]

        except ClassLevel.DoesNotExist:
            auto_feats_post = []

        for feat in auto_feats_post:
            CharacterFeature.objects.create(
                character=character,
                feature=feat,
                level=next_level
            )
        # C.1) LINEAR subclasses: auto-grant this level’s subclass features for the active choice
        # ensure we have the features for THIS class+level
        # F) LINEAR subclasses: auto-grant this level’s subclass features for the now-saved choice
        try:
            cl_linear = (
                ClassLevel.objects
                .prefetch_related('features__subclasses', 'features__subclass_group')
                .get(character_class=picked_cls, level=cls_level_after_post)
            )
            base_feats_for_level = list(cl_linear.features.all())
        except ClassLevel.DoesNotExist:
            base_feats_for_level = []

        for grp in picked_cls.subclass_groups.filter(system_type=SubclassGroup.SYSTEM_LINEAR):
            active_sub = _active_subclass_for_group(character, grp, None, base_feats_for_level)
            if not active_sub:
                continue
            grant_feats = _linear_feats_for_level(picked_cls, grp, active_sub, cls_level_after_post, base_feats_for_level)
            for sf in grant_feats:
                CharacterFeature.objects.get_or_create(
                    character=character,
                    feature=sf,
                    subclass=active_sub,
                    defaults={"level": next_level}
                )



        # D) general_feat + asi
        if level_form.cleaned_data.get('general_feat'):
            CharacterFeat.objects.create(
                character=character,
                feat=level_form.cleaned_data['general_feat'],
                level=next_level
            )
        # NEW: persist the actual ability increases
        asi_mode = level_form.cleaned_data.get("asi_mode")
        if asi_mode:
            a = (level_form.cleaned_data.get("asi_a") or "").strip()
            b = (level_form.cleaned_data.get("asi_b") or "").strip()

            valid_fields = {"strength","dexterity","constitution","intelligence","wisdom","charisma"}
            if a not in valid_fields or (b and b not in valid_fields):
                raise ValidationError("Invalid ASI field(s).")

            if asi_mode == "1+1":
                setattr(character, a, getattr(character, a) + 1)
                setattr(character, b, getattr(character, b) + 1)

            elif asi_mode == "1":
                setattr(character, a, getattr(character, a) + 1)

            elif asi_mode == "2":
                # If UI sent two different fields with mode "2", normalize to +1/+1.
                if b and b != a:
                    setattr(character, a, getattr(character, a) + 1)
                    setattr(character, b, getattr(character, b) + 1)
                else:
                    setattr(character, a, getattr(character, a) + 2)

            else:
                raise ValidationError("Invalid ASI mode.")

            character.save()


            # keep your audit row that “an ASI happened this level”
            CharacterFeature.objects.create(
                character=character,
                feature=None,
                level=next_level
            )

        chosen_subclass_by_group = {}
        # E) subclass choices & feature options
        for name, val in level_form.cleaned_data.items():
            

            if name.startswith('feat_') and val:
                feat_pk = int(name.split('_')[1])
                cf      = ClassFeature.objects.get(pk=feat_pk)
                if name.endswith('_subclass'):
                    sub = cf.subclass_group.subclasses.get(pk=int(val))
                    grp = cf.subclass_group

                    # 1) record the *choice* feature
                    CharacterFeature.objects.create(
                        character=character,
                        feature=cf,
                        subclass=sub,
                        level=next_level
                    )

                    # 2) also GRANT the subclass features that unlock *at this level*
                    grant_feats = []

                    if grp.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
                        # tiers that unlock now
                        unlock_tiers = _unlocked_tiers(grp, cls_level_after_post)

                        grant_feats = list(
                            ClassFeature.objects
                                .filter(scope='subclass_feat', subclass_group=grp, subclasses=sub, tier__in=unlock_tiers)
                                .filter(Q(level_required__isnull=True) | Q(level_required__lte=cls_level_after_post))
                                .filter(Q(min_level__isnull=True)      | Q(min_level__lte=cls_level_after_post))
                        )

                    else:
                        grant_feats = _linear_feats_for_level(picked_cls, grp, sub, cls_level_after_post, base_feats_for_level)


                    # 3) persist the unlocked subclass features
                    for sf in grant_feats:
                        CharacterFeature.objects.get_or_create(
                            character=character,
                            feature=sf,
                            subclass=sub,
                            level=next_level
                        )
                    chosen_subclass_by_group[grp.id] = sub.pk  
                elif name.endswith('_option'):
                    # (unchanged) record option
                    opt = cf.options.get(pk=int(val))
                    CharacterFeature.objects.create(
                        character=character,
                        feature=cf,
                        option=opt,
                        level=next_level
                    )
                elif name.endswith('_subfeats'):
                    grp = cf.subclass_group
                    per = max(1, int(getattr(grp, "modules_per_mastery", 2)))
                    picks_per_trigger = _picks_for_trigger(cf, picked_cls, cls_level_after_post)
                    gainer_cap = int(getattr(cf, "mastery_rank", 0) or 0)

                    picked_features = list(val) if hasattr(val, '__iter__') else []
                    if len(picked_features) != picks_per_trigger:
                        messages.error(request, f"Pick exactly {picks_per_trigger} feature(s) for {grp.name}.")
                        return redirect('characters:character_detail', pk=pk)

                    # Map current tier by subclass (after previous picks, before this trigger)
                    from django.db.models import Count
                    taken_by_sub = dict(
                        CharacterFeature.objects.filter(
                            character=character,
                            feature__scope='subclass_feat',
                            feature__subclass_group=grp
                        ).values('subclass_id').annotate(cnt=Count('id'))

                        .values_list('subclass_id', 'cnt')
                    )
                    current_tier_by_sub = {}
                    for sub in grp.subclasses.all():
                        taken = int(taken_by_sub.get(sub.id, 0))
                        current_tier_by_sub[sub.id] = 1 + (taken // per)

                    owned_feat_ids = set(
                        CharacterFeature.objects.filter(
                            character=character, feature__scope='subclass_feat',
                            feature__subclass_group=grp
                        ).values_list('feature_id', flat=True)
                    )

                    # Validate each pick against its own subclass tier/cap
                    to_create = []
                    for sf in picked_features:
                        # determine which subclass this feature belongs to (expect exactly one)
                        # determine which subclass this feature belongs to (expect exactly one)
                        subs = list(sf.subclasses.filter(group=grp))

                        if len(subs) != 1:
                            messages.error(request, f"Feature “{sf.name}” is not tied to exactly one subclass.")
                            return redirect('characters:character_detail', pk=pk)
                        sub = subs[0]

                        if sf.id in owned_feat_ids:
                            messages.error(request, f"You already own “{sf.name}”.")
                            return redirect('characters:character_detail', pk=pk)

                        allowed_cap = current_tier_by_sub.get(sub.id, 1)
                        if gainer_cap:
                            allowed_cap = min(allowed_cap, gainer_cap)

                        # if feature has a mastery_rank, enforce it
                        mr = getattr(sf, "mastery_rank", None)
                        if mr and int(mr) > int(allowed_cap):
                            messages.error(request,
                                        f"“{sf.name}” requires tier {mr}, but your allowed tier for {sub.name} is {allowed_cap}.")
                            return redirect('characters:character_detail', pk=pk)

                        to_create.append((sf, sub))

                    # Save all valid picks
                    for sf, sub in to_create:
                        CharacterFeature.objects.get_or_create(
                            character=character,
                            feature=sf,
                            subclass=sub,
                            defaults={"level": next_level}
                        )

                                                        



                # F) class_feat_pick & skill_feat_pick

        # 1) Class Feat (unchanged behavior)
        pick = level_form.cleaned_data.get('class_feat_pick')
        if pick:
            CharacterFeat.objects.create(
                character=character,
                feat=pick,
                level=next_level
            )

        # 2) Skill Feat(s) – honor ClassSkillFeatGrant.num_picks at this new class level
        # Recompute the grant for the ACTUAL class/level we just advanced in
        skill_grant_post = (
            ClassSkillFeatGrant.objects
            .filter(character_class=picked_cls, at_level=cls_level_after_post)
            .first()
        )

        if skill_grant_post and "skill_feat_pick" in level_form.cleaned_data:
            chosen = level_form.cleaned_data["skill_feat_pick"]

            # Normalize to a list
            if chosen is None:
                chosen_list = []
            elif hasattr(chosen, "__iter__") and not isinstance(chosen, (str, bytes)):
                chosen_list = list(chosen)
            else:
                chosen_list = [chosen]

            # Enforce exact count if num_picks > 0
            need = int(skill_grant_post.num_picks or 0)
            if need > 0 and len(chosen_list) != need:
                messages.error(
                    request,
                    f"You must pick exactly {need} Skill Feat{'s' if need != 1 else ''}."
                )
                return redirect('characters:character_detail', pk=pk)

            # Persist the selected skill feats
            for sf in chosen_list:
                # Safety: only allow feats typed "Skill" (should already be enforced by queryset)
                if (sf.feat_type or "").strip().lower() != "skill":
                    continue
                CharacterFeat.objects.create(
                    character=character,
                    feat=sf,
                    level=next_level
                )


        # G) martial_mastery
        mm = level_form.cleaned_data.get('martial_mastery')
        if mm:
            CharacterFeature.objects.create(
                character=character,
                feature=None,
                level=next_level
            )
        # Manual add (feat/feature/racial_feature) with explanation

        # H) Starting skills — only when this is the first level in the chosen class
        if cls_level_after_post == 1:
            trained = (ProficiencyLevel.objects
                    .filter(name__iexact="Trained").order_by("bonus").first())
            if not trained:
                messages.error(request, "Missing proficiency levels (need at least ‘Trained’). Please seed the tiers and try again.")
                return redirect('characters:character_detail', pk=pk)            
            raw_picks = request.POST.getlist("starting_skill_picks")  # ← from <select multiple>

            # Cap based on the picked class (mods-based formula now)
            cap = _starting_skills_cap_for(picked_cls)
            if cap and len(raw_picks) > cap:
                raw_picks = raw_picks[:cap]  # hard-enforce; or flash a message if you prefer

            if raw_picks:
                trained = (ProficiencyLevel.objects
                        .filter(name__iexact="Trained").order_by("bonus").first())
                if not trained:
                    trained = (ProficiencyLevel.objects
                            .exclude(name__iregex=r'(?i)untrained').order_by("bonus").first())

                ct_skill = ContentType.objects.get_for_model(Skill)
                ct_sub   = ContentType.objects.get_for_model(SubSkill)

                for token in raw_picks:
                    try:
                        if token.startswith("sk_"):
                            sid = int(token[3:])
                            CharacterSkillProficiency.objects.get_or_create(
                                character=character,
                                selected_skill_type=ct_skill,
                                selected_skill_id=sid,
                                defaults={"proficiency": trained},
                            )
                        elif token.startswith("sub_"):
                            sid = int(token[4:])
                            CharacterSkillProficiency.objects.get_or_create(
                                character=character,
                                selected_skill_type=ct_sub,
                                selected_skill_id=sid,
                                defaults={"proficiency": trained},
                            )
                    except ValueError:
                        pass
        # --- Apply Skill-Feat grant(s) --------------------------------------------
        skill_grant = (
            ClassSkillFeatGrant.objects
            .filter(character_class=posted_cls, at_level=cls_level_for_validate)
            .first()
        )
        if skill_grant and "skill_feat_pick" in level_form.fields:
            picks = int(skill_grant.num_picks or 0)
            if picks > 0:
                picked = level_form.cleaned_data.get("skill_feat_pick")
                # Normalize to a list
                if isinstance(level_form.fields["skill_feat_pick"], forms.ModelMultipleChoiceField):
                    picked_feats = list(picked)
                    if len(picked_feats) != picks:
                        level_form.add_error("skill_feat_pick", f"Pick exactly {picks} skill feat(s).")
                        return redirect('characters:character_detail', pk=pk)
                else:
                    picked_feats = [picked] if picked else []
                    if len(picked_feats) != picks:
                        level_form.add_error("skill_feat_pick", f"Pick exactly {picks} skill feat(s).")
                        return redirect('characters:character_detail', pk=pk)

                # Persist as CharacterFeat at the *new* total level
                next_total_level = character.level + 1
                for feat_obj in picked_feats:
                    CharacterFeat.objects.get_or_create(
                        character=character,
                        feat=feat_obj,
                        defaults={"level": next_total_level}
                    )

        # --- Skill points grant for THIS level-up ---
        pts = int(getattr(picked_cls, "skill_points_per_level", 0) or 0)
        if pts:
            CharacterSkillPointTx.objects.create(
                character=character,
                amount=pts,
                source="level_award",
                reason=f"{picked_cls.name} L{cls_level_after_post}",
                at_level=next_level,
                awarded_class=picked_cls,
            )
            messages.success(request, f"Gained {pts} skill point(s) from {picked_cls.name}.")


        # ---- DONE: all mutations saved; switch to PRG to avoid stale context ----
        messages.success(request, f"{character.name} advanced to level {next_level}.")
        return redirect('characters:character_detail', pk=pk)

    # Keep every statement in order (A..H in your comments):
    #   - create/update CharacterClassProgress
    #   - bump character.level
    #   - grant auto features (class_feat, spell tables)
    #   - LINEAR subclass auto-grants (at this level)
    #   - general_feat, ASI application
    #   - loop over `level_form.cleaned_data` for subclass picks / options / subfeats
    #   - class_feat_pick persistence
    #   - skill_feat_pick count enforcement & persistence (using skill_grant_post)
    #   - martial_mastery note
    #   - starting skills (cls_level_after_post == 1) using _starting_skills_cap_for
    #   - skill points grant, success message
    #
    # IMPORTANT: keep all `messages.*` and `return redirect(...)` calls unchanged.

    # (The code you paste here should end with:)
    # messages.success(request, f"{character.name} advanced to level {next_level}.")
    return redirect('characters:character_detail', pk=pk)

from django.views.decorators.http import require_POST

@login_required
def set_field_override(request, pk):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only.")
    character = get_object_or_404(Character, pk=pk, user=request.user)

    base_key = (request.POST.get("key") or "").strip()       # e.g. "prof:armor"
    if not base_key:
        return HttpResponseBadRequest("Missing key.")

    formula = (request.POST.get("formula") or "").strip()    # e.g. "base + prof + half + dex_mod"
    value   = (request.POST.get("value") or "").strip()      # final override (int) or blank

    # store/remove formula override
    fkey = f"formula:{base_key}"
    if formula:
        CharacterFieldOverride.objects.update_or_create(
            character=character, key=fkey, defaults={"value": formula}
        )
    else:
        CharacterFieldOverride.objects.filter(character=character, key=fkey).delete()

    # store/remove final number override
    vkey = f"final:{base_key}"
    if value != "":
        CharacterFieldOverride.objects.update_or_create(
            character=character, key=vkey, defaults={"value": value}
        )
    else:
        CharacterFieldOverride.objects.filter(character=character, key=vkey).delete()

    # return 204 for AJAX, or redirect if you prefer full post/redirect/get
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect("characters:character_detail", pk=pk)



from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import (
    Character, CharacterClassProgress, ClassLevel, UniversalLevelFeature,
    CharacterFeature, ClassFeature, ClassSubclass, FeatureOption
)
from .forms import LevelUpForm
class ClassFeatAutocomplete(AutoResponseView):
     model = ClassFeat
     search_fields = ['name__icontains']

     def get_queryset(self):
         qs = super().get_queryset()
         lvl  = self.request.GET.get("level")
         race = self.request.GET.get("race")
         if lvl:
             qs = qs.filter(Q(level_prerequisite__icontains=lvl) | Q(level_prerequisite__exact=""))
         if race:
             qs = qs.filter(Q(race__iexact=race) | Q(race__exact=""))
         return qs


class PreviewForm(forms.Form):
    base_class = forms.ModelChoiceField(
        queryset=CharacterClass.objects.order_by('name'),
        label="Preview a different class",
        widget=forms.Select(attrs={
            'class': 'form-select', 
            'id': 'preview_class_select'
        })
    )

from django.http import HttpResponse
