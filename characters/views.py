from django.shortcuts import render
from django.contrib import messages

from django.db.models import Case, When, IntegerField
# Create your views here.
# characters/views.py
from django.db.models import Q, Max
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django_select2.views import AutoResponseView
from django.db.models import Count
from .models import Character, Skill  
from campaigns.models import Campaign
from django.db import models
import math
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
FIVE_TIERS = ["Untrained", "Trained", "Expert", "Master", "Legendary"]

def _is_untrained_name(name: str | None) -> bool:
    return (name or "").strip().lower() == "untrained"

from django.contrib.contenttypes.models import ContentType
@login_required
def character_list(request):
    characters = request.user.characters.all()
    return render(request, 'forge/character_list.html', {'characters': characters})


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

@login_required
@require_POST
def add_known_spell(request, pk):
    character = get_object_or_404(Character, pk=pk, user=request.user)
    spell_id  = request.POST.get("spell_id")
    origin    = (request.POST.get("origin") or "").lower()
    rank      = int(request.POST.get("rank") or 1)

    try:
        sp = Spell.objects.get(pk=int(spell_id))
    except (ValueError, Spell.DoesNotExist):
        return HttpResponseBadRequest("Invalid spell_id")

    rec, _ = CharacterKnownSpell.objects.update_or_create(
        character=character, spell=sp,
        defaults={"origin": origin, "rank": rank}
    )
    return JsonResponse({"ok": True, "id": rec.id})

@login_required
@require_POST
def set_prepared_spell(request, pk):
    character = get_object_or_404(Character, pk=pk, user=request.user)
    spell_id  = request.POST.get("spell_id")
    origin    = (request.POST.get("origin") or "").lower()
    rank      = int(request.POST.get("rank") or 1)
    action    = (request.POST.get("action") or "add").lower()

    try:
        sp = Spell.objects.get(pk=int(spell_id))
    except (ValueError, Spell.DoesNotExist):
        return HttpResponseBadRequest("Invalid spell_id")

    if action == "remove":
        CharacterPreparedSpell.objects.filter(
            character=character, spell=sp, origin=origin, rank=rank
        ).delete()
        return JsonResponse({"ok": True, "removed": True})

    rec, _ = CharacterPreparedSpell.objects.get_or_create(
        character=character, spell=sp, origin=origin, rank=rank
    )
    return JsonResponse({"ok": True, "id": rec.id})
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


def _active_subclass_for_group(character, grp, level_form, base_feats):
    """
    Determine which subclass is active for this group:
    1) If this same level includes a new subclass_choice radio and it’s selected, use that.
    2) Otherwise, use the last saved subclass for this group.
    """
    # find the subclass_choice feature for this group on this screen (if any)
    sc_feats = [f for f in base_feats
                if isinstance(f, ClassFeature)
                and f.scope == 'subclass_choice'
                and f.subclass_group_id == grp.id]
    if sc_feats:
        fn = f"feat_{sc_feats[0].pk}_subclass"
        if fn in level_form.fields:
            val = level_form[fn].value()
            if val:
                try:
                    return grp.subclasses.get(pk=int(val))
                except (ValueError, ClassSubclass.DoesNotExist):
                    pass

    # fallback: whatever the character already chose earlier for this group
    prev = (CharacterFeature.objects
            .filter(character=character,
                    subclass__group=grp,
                    feature__scope='subclass_choice')
            .order_by('-level')
            .first())
    return prev.subclass if prev else None




def spell_list(request):
    spells = Spell.objects.all()

    query = request.GET.get('q')
    if query:
        spells = spells.filter(name__icontains=query) | spells.filter(tags__icontains=query)

    level = request.GET.get('level')
    if level:
        spells = spells.filter(level=level)

    spells = spells.order_by('level', 'name')

    levels = sorted(set(spells.values_list('level', flat=True)))

    # ✅ Fixed 4 origins
    origins = ["Arcane", "Divine", "Primal", "Occult"]

    # ✅ Split classification keywords across all spells
    classifications_raw = Spell.objects.values_list('classification', flat=True)
    classifications = sorted({tag.strip() for string in classifications_raw for tag in string.split(',') if tag.strip()})

    return render(request, 'codex/spell_list.html', {
        'spells': spells,
        'levels': levels,
        'origins': origins,
        'classifications': classifications,
        'query': query,
        'selected_level': level,
    })




WORD_BOUNDARY = r'\b{}\b'

def feat_list(request):
    feats = ClassFeat.objects.all()

    # ——— text search “q” ———
    q = request.GET.get('q')
    if q:
        feats = feats.filter(name__icontains=q) | feats.filter(tags__icontains=q)

    # ——— feat_type filter ———
    ft = request.GET.get('type')
    if ft:
        # match “Thievery” won’t catch “Rogue”, but “Rogue” catches “Rogue (Thief)”
        pattern = WORD_BOUNDARY.format(re.escape(ft))
        feats = feats.filter(feat_type__iregex=pattern)

    # ——— class filter ———
    cls = request.GET.get('class')
    if cls:
        pattern = WORD_BOUNDARY.format(re.escape(cls))
        feats = feats.filter(class_name__iregex=pattern)

    # ——— race filter ———
    rc = request.GET.get('race')
    if rc:
        pattern = WORD_BOUNDARY.format(re.escape(rc))
        feats = feats.filter(race__iregex=pattern)

    feats = feats.order_by('name')

    # ——— tabs (full feat_type strings) ———
    types = sorted(set(feats.values_list('feat_type', flat=True)))

    # ——— dropdown lists ———
    raw_feat_types = feats.values_list('feat_type', flat=True)
    feat_types = sorted({
        part.strip()
        for full in raw_feat_types
        for part in full.split(',')
        if part.strip()
    })

    raw_classes = feats.values_list('class_name', flat=True)
    class_names = sorted({
        part.strip()
        for full in raw_classes
        for part in full.split(',')
        if part.strip()
    })

    raw_races = feats.values_list('race', flat=True)
    race_names = sorted({
        part.strip()
        for full in raw_races
        for part in full.split(',')
        if part.strip()
    })
    

    return render(request, 'codex/feat_list.html', {
        'feats':          feats,
        'types':          types,
        'feat_types':     feat_types,
        'class_names':    class_names,
        'race_names':     race_names,
        # so your template can re-check the boxes on reload
        'selected_type':  ft,
        'selected_class': cls,
        'selected_race':  rc,
        'query':          q,
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
                    .prefetch_related('subclasses'),
              )
          )
    )

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
                )
                for f in modular_feats:
                    lvl = tier_map.get(f.tier)
                    if lvl:
                        fbylevel.setdefault(lvl, []).append(f)

            else:
                # existing “linear” logic
                for cl in levels:
                    feats = [
                        f for f in cl.features.all()
                        if f.scope == 'subclass_feat' and sub in f.subclasses.all()
                    ]
                    if feats:
                        fbylevel.setdefault(cl.level, []).extend(feats)

            # Sort by level so L2 comes before L5, etc.
            sub.features_by_level = OrderedDict(sorted(fbylevel.items()))
 

    # ── 5) Summary 1…20 ────────────────────────────────────────────────────────
    max_lvl = max(levels.aggregate(Max('level'))['level__max'] or 1, 20)
    summary = []
    for lvl in range(1, max_lvl + 1):
        cl = next((c for c in levels if c.level == lvl), None)
        feats = list(cl.features.all()) if cl else []

        labels = []
        for f in feats:
            if f.scope == 'subclass_feat':
                names = [s.group.name for s in f.subclasses.all()]
                labels.append(names[0] if names else f"{f.code}–{f.name}")
            else:
                labels.append(f"{f.code}–{f.name}")

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

def race_detail(request, pk):
    race = get_object_or_404(Race, pk=pk)
    return render(request, 'codex/race_detail.html', {'race': race})

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
            # 1) persist the Character
            character = form.save(commit=False)
            character.user = request.user
            character.save()

            # 2) parse & save the computed skill proficiencies JSON
            raw = form.cleaned_data.get('computed_skill_proficiencies') or '{}'
            try:
                prof_map = json.loads(raw)
                for full_name, tier_name in prof_map.items():
                    # "Athletics – Climbing"
                    category, subname = full_name.split(' – ', 1)
                    subskill = SubSkill.objects.get(name=subname, skill__name=category)
                    prof     = ProficiencyLevel.objects.get(name__iexact=tier_name)
                    CharacterSkillProficiency.objects.create(
                        character=character,
                        subskill=subskill,
                        proficiency=prof
                    )
            except (ValueError, SubSkill.DoesNotExist, ProficiencyLevel.DoesNotExist):
                # ignore any parse/look-up errors
                pass

            return redirect('characters:character_list')


    else:
        form = CharacterCreationForm()

    # prepare JSON for frontend
    races = []
    for race in Race.objects.prefetch_related('subraces').all():
        races.append({
            'code': race.code,
            'name': race.name,
            'modifiers': {
                'Strength':     race.strength_bonus,
                'Dexterity':    race.dexterity_bonus,
                'Constitution': race.constitution_bonus,
                'Intelligence': race.intelligence_bonus,
                'Wisdom':       race.wisdom_bonus,
                'Charisma':     race.charisma_bonus,
            },
            'free_points':           race.free_points,
           'max_bonus_per_ability': race.max_bonus_per_ability,
            'subraces': [
                {
                    'code': sub.code,
                    'name': sub.name,
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
            'primary': {
                'ability': bg.get_primary_ability_display(),
                'bonus':   bg.primary_bonus,
                'skill':   bg.primary_skill.name,
            },
            'secondary': {
                'ability': bg.get_secondary_ability_display(),
                'bonus':   bg.secondary_bonus,
                'skill':   bg.secondary_skill.name,
            }
        })

    context = {
        'form':             form,
        'races_json':       json.dumps(races,       cls=DjangoJSONEncoder),
        'backgrounds_json': json.dumps(backgrounds, cls=DjangoJSONEncoder),
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



@login_required
def character_detail(request, pk):
    # ── 1) Load character & basic sheet context ─────────────────────────────
    character = get_object_or_404(Character, pk=pk, user=request.user)
    can_edit  = request.user == character.user

    ability_map = {
        'Strength':     character.strength,
        'Dexterity':    character.dexterity,
        'Constitution': character.constitution,
        'Intelligence': character.intelligence,
        'Wisdom':       character.wisdom,
        'Charisma':     character.charisma,
    }
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
    skill_proficiencies = list(
        character.skill_proficiencies.select_related('proficiency').all()
    )
    skill_proficiencies.sort(key=lambda sp: sp.selected_skill.name)
    class_progress  = character.class_progress.select_related('character_class')
    racial_features = character.race.features.all() if character.race else []
    universal_feats = UniversalLevelFeature.objects.filter(level=character.level)
    total_level     = character.level
    subrace_name    = (character.subrace.name 
                       if getattr(character, 'subrace', None) else None)

    # ── 2) Determine which class we’re leveling in / previewing ───────────
    next_level = total_level + 1
    first_prog = class_progress.first()
    default_cls = first_prog.character_class if first_prog else CharacterClass.objects.first()

    # If a GET param “base_class” is present, use that; otherwise use default
    selected_pk = (request.POST.get('base_class') or request.GET.get('base_class'))
    if selected_pk and str(selected_pk).isdigit():
        preview_cls = CharacterClass.objects.get(pk=int(selected_pk))
    else:
        preview_cls = default_cls

    subclass_groups = list(
    preview_cls.subclass_groups
        .order_by('name')
        .prefetch_related('subclasses', 'tier_levels')
)
    cls_level_after = _class_level_after_pick(character, preview_cls)
    cls_level_after_post = cls_level_after
    try:
        cl = (
            ClassLevel.objects
            .prefetch_related(
                'features__subclasses',
                'features__subclass_group',
                'features__options__grants_feature',   # ← ADD
            )
            .get(character_class=preview_cls, level=cls_level_after)

        )
        base_feats = list(cl.features.all())
    except ClassLevel.DoesNotExist:
        base_feats = []
    grants_class_feat = any(
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

    def _mod(score: int) -> int:
        return (score - 10) // 2

    spellcasting_blocks = []
    for cp in class_progress:
        # spell-table features this character actually owns for this class
        owned_tables = (ClassFeature.objects
            .filter(kind="spell_table",
                    character_class=cp.character_class,
                    character_features__character=character)
            .distinct())
        for ft in owned_tables:
            row = ft.spell_slot_rows.filter(level=cp.levels).first()

            # safe eval helpers for formulas stored on the feature
            ctx = {
                "level": cp.levels,
                "strength": character.strength,      "str_mod": _mod(character.strength),
                "dexterity": character.dexterity,    "dex_mod": _mod(character.dexterity),
                "constitution": character.constitution,"con_mod": _mod(character.constitution),
                "intelligence": character.intelligence,"int_mod": _mod(character.intelligence),
                "wisdom": character.wisdom,          "wis_mod": _mod(character.wisdom),
                "charisma": character.charisma,      "cha_mod": _mod(character.charisma),
                "floor": math.floor, "ceil": math.ceil, "min": min, "max": max,
            }
            def _eval(expr):
                if not expr: return None
                try:
                    return eval(expr, {"__builtins__": {}}, ctx)
                except Exception:
                    return None

            slots = []
            if row:
                slots = [row.slot1,row.slot2,row.slot3,row.slot4,row.slot5,
                        row.slot6,row.slot7,row.slot8,row.slot9,row.slot10]

            spellcasting_blocks.append({
                "klass": cp.character_class,                 # class name in template
                "list": ft.get_spell_list_display() or ft.spell_list,  # Arcane/Divine/…
                "slots": slots,                              # 10 ints
                "cantrips": _eval(ft.cantrips_formula) or 0,
                "known": _eval(ft.spells_known_formula),     # may be None for prepared casters
                "prepared": _eval(ft.spells_prepared_formula),
            })


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
 
    if request.method == "POST" and "edit_character_submit" in request.POST and can_edit:

        if request.method == "POST" and "update_details_submit" in request.POST and can_edit:
            details_form = CharacterDetailsForm(request.POST, instance=character)
            if details_form.is_valid():
                details_form.save()
                return redirect('characters:character_detail', pk=pk)
            # fall through to render with errors if invalid


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


    manual_form = ManualGrantForm(request.POST or None) if can_edit else None
    # NEW: independent handler for “Manually Add Item”
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


    # bind LevelUpForm on GET (so base_class stays selected) *and* on POST
    data = request.POST if request.method == 'POST' else request.GET
    level_form = LevelUpForm(
        data or None,
        character=character,
        to_choose=to_choose,
        uni=uni,
        preview_cls=preview_cls,
        grants_class_feat=grants_class_feat
    )
    if grants_class_feat and "class_feat_pick" not in level_form.fields:
        level_form.fields["class_feat_pick"] = forms.ModelChoiceField(
            queryset=ClassFeat.objects.all(), # filled by the filter block below
            required=True,
            label="Class Feat"
        )
    # INIT HERE so we can append immediately below
    feature_fields = []

    gain_sub_feat_triggers = [
        f for f in to_choose
        if isinstance(f, ClassFeature) and f.scope == 'gain_subclass_feat'
    ]

    for trigger in gain_sub_feat_triggers:
        grp = trigger.subclass_group
        if not grp:
            continue

        field_name = f"feat_{trigger.pk}_subfeats"

        # default empty
        eligible_qs = ClassFeature.objects.none()
        active_sub = None  # only relevant for LINEAR or MASTERY

        # ---------------- LINEAR ----------------
        if grp.system_type == SubclassGroup.SYSTEM_LINEAR:
            active_sub = _active_subclass_for_group(character, grp, level_form, base_feats)

            feats_now = []
            if active_sub:
                try:
                    cl_next = (ClassLevel.objects
                            .prefetch_related('features__subclasses', 'features__subclass_group')
                            .get(character_class=preview_cls, level=cls_level_after))
                    feats_now = [
                        f for f in cl_next.features.all()
                        if f.scope == 'subclass_feat'
                        and f.subclass_group_id == grp.id
                        and (active_sub in f.subclasses.all())
                        and (f.level_required is None or f.level_required <= cls_level_after)
                    ]
                except ClassLevel.DoesNotExist:
                    feats_now = list(
                        ClassFeature.objects.filter(
                            scope='subclass_feat',
                            subclass_group=grp,
                            subclasses=active_sub,
                            level_required=cls_level_after

                        )
                    )

            eligible_qs = ClassFeature.objects.filter(pk__in=[f.pk for f in feats_now])

            # no choices to make; still add a stable field (not required)
            level_form.fields[field_name] = forms.ModelMultipleChoiceField(
                queryset=eligible_qs,
                required=False,
                widget=forms.CheckboxSelectMultiple
            )

            feature_fields.append({
                "kind": "gain_subclass_feat",
                "label": f"Gain Subclass Feature – {grp.name}",
                "field": level_form[field_name],
                "group": grp,
                "subclass": active_sub,
                "eligible": list(eligible_qs),
                "system": grp.system_type,
            })
            continue

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
                    .filter(scope='subclass_feat', subclass_group=grp, subclasses=sub)
                    .filter(tier__in=unlock_tiers)
                    .filter(Q(level_required__isnull=True) | Q(level_required__lte=cls_level_after))
                    .filter(Q(min_level__isnull=True)      | Q(min_level__lte=cls_level_after))
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

        # ------------- MODULAR MASTERY -------------
        if grp.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
            # your existing mastery logic (requires a specific subclass)
            active_sub = _active_subclass_for_group(character, grp, level_form, base_feats)

            eligible_qs = ClassFeature.objects.none()
            if active_sub:
                rules = active_sub.modular_rules or {}
                modules_per_mastery = int(rules.get('modules_per_mastery', 2))

                taken_ids = set(
                    CharacterFeature.objects
                    .filter(character=character, subclass=active_sub, feature__scope='subclass_feat')
                    .values_list('feature_id', flat=True)
                )
                taken_count = len(taken_ids)
                current_mastery = taken_count // max(1, modules_per_mastery)

                eligible_qs = (ClassFeature.objects
                            .filter(scope='subclass_feat',
                                    subclass_group=grp,
                                    subclasses=active_sub)
                            .exclude(pk__in=taken_ids)
                            .filter(
                                models.Q(mastery_rank__isnull=True) |
                                models.Q(mastery_rank__lte=current_mastery)
                            )
                            .filter(
                                models.Q(min_level__isnull=True) |
                                models.Q(min_level__lte=cls_level_after)
                            ))


            level_form.fields[field_name] = forms.ModelMultipleChoiceField(
                label=f"Pick {grp.name} feature(s)",
                queryset=eligible_qs.order_by('name'),
                required=bool(eligible_qs.exists()),
                widget=forms.CheckboxSelectMultiple
            )

            feature_fields.append({
                "kind": "gain_subclass_feat",
                "label": f"Gain Subclass Feature – {grp.name}",
                "field": level_form[field_name],
                "group": grp,
                "subclass": active_sub,
                "eligible": list(eligible_qs),
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
        cls_after = cls_level_after           # class level after this pick
        cls_name  = preview_cls.name

        # Collect role tags from the class, normalized to lower
        class_tags = [t.lower() for t in preview_cls.tags.values_list("name", flat=True)]

        # Build token list we will accept as a "membership" match
        #   - specific class name
        #   - class role tags (e.g., Spellcaster, Martial)
        #   - a few safe synonyms for Spellcaster so we catch messy data
        tokens = [cls_name] + class_tags
        if "spellcaster" in class_tags:
            tokens += ["spellcaster", "spellcasting", "caster"]
        if "martial" in class_tags:
            tokens += ["martial"]

        # Turn tokens into an OR'd, word-boundary style iregex that tolerates lists
        # (comma/semicolon/slash/space separated)
        token_res = [
            rf'(^|[,;/\s]){re.escape(tok)}([,;/\s]|$)'
            for tok in tokens if tok
        ]
        any_token_re = "(" + ")|(".join(token_res) + ")" if token_res else None

        # Start from Class feats
        base = ClassFeat.objects.filter(feat_type__iexact="Class")

        # Accept if:
        #  - class_name contains the specific class name OR one of the role tags, OR
        #  - tags contains one of the role tags, OR
        #  - class_name is empty/NULL, OR
        #  - class_name says "All Classes" / "Any Class"
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

        # Parse free-text level prerequisite (e.g., "3rd level", "Druid 1st level or higher")
        eligible_ids = [
            f.pk for f in qs
            if parse_req_level(getattr(f, "level_prerequisite", "")) <= cls_after
        ]

        # If we still somehow filtered everything out (dirty data), fall back to:
        #  - just Class feats whose class_name includes the specific class OR is blank/"All Classes"
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
                        # LINEAR: prefer features attached to this ClassLevel
                        try:
                            cl_next = (
                                ClassLevel.objects
                                .prefetch_related(
                                    'features__subclasses',
                                    'features__subclass_group',
                                    'features__options__grants_feature',   # ← ADD
                                )
                                .get(character_class=picked_cls, level=cls_level_after_post)
                            )

                            grant_feats = [
                                f for f in cl_next.features.all()
                                if f.scope == 'subclass_feat'
                                and f.subclass_group_id == grp.id
                                and sub in f.subclasses.all()
                            ]
                        except ClassLevel.DoesNotExist:
                            # fallback: explicit level_required
                            grant_feats = list(
                                ClassFeature.objects.filter(
                                    scope='subclass_feat',
                                    subclass_group=grp,
                                    subclasses=sub,
                                    level_required=cls_level_after_post

                                )
                            )

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
                    # NEW: persist selected subclass features for modular systems
                    grp = cf.subclass_group

                    # ModelMultipleChoiceField returns ClassFeature objects
                    picked_features = list(val) if hasattr(val, '__iter__') else []

                    for sf in picked_features:
                        # attach to the subclass this feature belongs to
                        sub_for_sf = sf.subclasses.first()
                        if not sub_for_sf:
                            continue
                        CharacterFeature.objects.get_or_create(
                            character=character,
                            feature=sf,
                            subclass=sub_for_sf,
                            level=next_level  # keep character-level here
                        )

                      



                # F) class_feat_pick & skill_feat_pick
        # F) pick a Class Feat only
        pick = level_form.cleaned_data.get('class_feat_pick')
        if pick:
            CharacterFeat.objects.create(
                character=character,
                feat=pick,
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
                subclasses=sc,
                subclass_group=grp,
            )

            if grp.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
                feats = list(
                    qs.filter(tier__in=unlock_tiers)
                    .filter(Q(level_required__isnull=True) | Q(level_required__lte=cls_level_after))
                    .filter(Q(min_level__isnull=True)      | Q(min_level__lte=cls_level_after))
                    .order_by('name')
                )

            elif grp.system_type == SubclassGroup.SYSTEM_LINEAR:
                # Prefer features linked to this ClassLevel
                feats = [
                    f for f in base_feats
                    if f.scope == 'subclass_feat'
                    and f.subclass_group_id == grp.id
                    and sc in f.subclasses.all()
                ]
                # Fallback: explicit level gating
                if not feats:
                    feats = list(
                        qs.filter(level_required=cls_level_after).order_by('name')
                    )
                # Extra safety for L1 data that forgot level_required
                if not feats and cls_level_after == 1:
                    feats = list(
                        qs.filter(Q(level_required=1) | Q(level_required__isnull=True))
                        .order_by('name')
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

    # Apply overrides to the proficiency summary’s modifier values (if present)
    prof_by_code = {r["type_code"]: r for r in _current_proficiencies_for_character(character)}
    for code, row in prof_by_code.items():
        ov = overrides.get(f"prof:{code}")
        if ov not in (None, ""):
            try:
                row["modifier"] = int(ov)
                row["source"]   = "Override"
            except ValueError:
                pass
    # Keep list form for template
    proficiency_summary = list(prof_by_code.values())
    half_lvl = _half_level_total(character.level)

    by_code = {r["type_code"]: r for r in proficiency_summary}
    def hl_if_trained(code: str) -> int:
        r = by_code.get(code)
        if not r: return 0
        return half_lvl if not _is_untrained_name(r.get("tier_name")) else 0
    # Pull armor choices from the Armor model


    # Armor picker: list + currently selected (by override)
    armor_list = list(Armor.objects.all().order_by('type','name').values('id','name','armor_value'))
    # Use overrides to determine equipped armor/value BEFORE computing derived stats
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
    prof_armor     = prof_by_code.get("armor",     {"modifier": 0})["modifier"]
    prof_dodge     = prof_by_code.get("dodge",     {"modifier": 0})["modifier"]
    prof_dc        = prof_by_code.get("dc",        {"modifier": 0})["modifier"]
    prof_reflex    = prof_by_code.get("reflex",    {"modifier": 0})["modifier"]
    prof_fort      = prof_by_code.get("fortitude", {"modifier": 0})["modifier"]
    prof_will      = prof_by_code.get("will",      {"modifier": 0})["modifier"]
    prof_weapon    = prof_by_code.get("weapon",    {"modifier": 0})["modifier"]
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
    hp_current = getattr(character, "hp_current", None) or getattr(character, "hp", None) or 0
    hp_max     = getattr(character, "hp_max", None)     or getattr(character, "max_hp", None) or 0
    temp_hp    = getattr(character, "temp_hp", 0)



    derived = {
        "half_level":      half_lvl,
        "armor_total":     (int(overrides.get("armor_value") or 0)) + prof_armor + hl_if_trained("armor"),
        "dodge_total":     10 + dex_mod + prof_dodge + hl_if_trained("dodge"),
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

    def add_row(code, abil_name=None, abil_mod_val=0, label=None, base_const=0):
        r = prof_by_code.get(code, {"tier_name":"—","modifier":0,"source":"—"})
        prof = int(r["modifier"])
        half = _hl(code)
        total = base_const + prof + half + (abil_mod_val if abil_name else 0)
        # build formula string
        parts_f = []
        parts_v = []
        if base_const:
            parts_f.append(str(base_const))
            parts_v.append(str(base_const))
        parts_f.append("prof");              parts_v.append(_fmt(prof))
        parts_f.append("½ level");           parts_v.append(_fmt(half))
        if abil_name:
            parts_f.append(f"{abil_name[:3]} mod")
            parts_v.append(_fmt(abil_mod_val))
        defense_rows.append({
            "type":   label or LABELS.get(code, code).title(),
            "tier":   r["tier_name"],
            "formula": " + ".join(parts_f),
            "values":  " + ".join(parts_v),
            "total_s": _fmt(total),
            "source": r["source"],
        })

    add_row("armor",                      label="Armor")
    add_row("dodge",  "Dexterity", dex_mod, label="Dodge", base_const=10)   # ← 10 + DEX + prof + ½ level
    add_row("reflex", "Dexterity", dex_mod, label="Reflex")
    add_row("fortitude","Constitution", con_mod, label="Fortitude")
    add_row("will",   "Wisdom",   wis_mod, label="Will")
    add_row("perception",               label="Perception")  # (no ability in your model)
    add_row("initiative",               label="Initiative")  # (no ability in your model)
    add_row("weapon",                   label="Weapon (base)")


    add_row("armor")
    add_row("dodge",      "Dexterity", dex_mod)
    add_row("reflex",     "Dexterity", dex_mod)
    add_row("fortitude",  "Constitution", con_mod)
    add_row("will",       "Wisdom", wis_mod)
    add_row("perception")     # no ability in your model
    add_row("initiative")     # no ability in your model
    add_row("weapon")         # base “to-hit” without ability

    # Weapon w/ abilities (for quick display)
    attack_rows = [
        {"label": "Weapon (base)", "total_s": _fmt(derived["weapon_base"]),
        "formula": "prof + ½ level", "values": f"{_fmt(prof_weapon)} + {_fmt(_hl('weapon'))}"},
        {"label": "Weapon (STR)",  "total_s": _fmt(derived["weapon_with_str"]),
        "formula": "prof + ½ level + STR mod",
        "values": f"{_fmt(prof_weapon)} + {_fmt(_hl('weapon'))} + {_fmt(str_mod)}"},
        {"label": "Weapon (DEX)",  "total_s": _fmt(derived["weapon_with_dex"]),
        "formula": "prof + ½ level + DEX mod",
        "values": f"{_fmt(prof_weapon)} + {_fmt(_hl('weapon'))} + {_fmt(dex_mod)}"},
    ]

    # Spell/DC rows (one per key ability)
    # Build Spell/DC values from key abilities, then produce rows for the template
    derived["spell_dcs"] = []
    for abil in key_abil_names:
        score = getattr(character, abil.lower(), 10)
        mod   = _abil_mod(score)
        derived["spell_dcs"].append({
            "ability": abil,
            "value": 8 + mod + prof_dc + hl_if_trained("dc"),
        })

    spell_dc_rows = []
    for s in derived["spell_dcs"]:
        abil = s["ability"]
        mod  = _abil_mod(getattr(character, abil.lower(), 10))
        spell_dc_rows.append({
            "label": f"Spell/DC ({abil})",
            "total": s["value"],
            "formula": "8 + ability mod + prof + ½ level",
            "values": f"8 + {_fmt(mod)} + {_fmt(prof_dc)} + {_fmt(_hl('dc'))}",
        })




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
                "id_key":    (f"sub_{obj.pk}" if is_sub else f"sk_{sk.pk}"),
                "is_sub":    is_sub,
                "skill_id":  sk.pk,
                "sub_id":    (obj.pk if is_sub else None),
                "label":     label,
                "ability1":  abil1.title(),
                "ability2":  abil2.title() if abil2 else None,
                "prof_id":   (prof.pk if prof else None),
                "prof_name": (prof.name if prof else "Untrained"),
                "prof_bonus": pbonus,
                "mod1":      a1_mod,
                "mod2":      a2_mod,
                "half":      h,              # NOTE: this is now 0 for Untrained
                "total1":    total1,
                "total2":    total2,
            }

            all_skill_rows.append(row)
    if request.method == "POST" and "save_skill_row" in request.POST and can_edit:
        key  = request.POST["save_skill_row"]  # e.g., "sk_5" or "sub_12"
        new_pk = request.POST.get(f"sp_{key}")
        note   = (request.POST.get(f"sp_note_{key}") or "").strip()

        if not new_pk:
            messages.error(request, "Pick a proficiency tier.")
            return redirect("characters:character_detail", pk=pk)
        if not note:
            messages.error(request, f"Please provide a reason for changing {key}.")
            return redirect("characters:character_detail", pk=pk)

        new_prof = ProficiencyLevel.objects.get(pk=int(new_pk))
        if key.startswith("sub_"):
            obj_id = int(key[4:])
            ctype  = ct_sub
        else:
            obj_id = int(key[3:])
            ctype  = ct_skill

        rec, created = CharacterSkillProficiency.objects.get_or_create(
            character=character,
            selected_skill_type=ctype,
            selected_skill_id=obj_id,
            defaults={"proficiency": new_prof},
        )
        if not created and rec.proficiency_id != new_prof.pk:
            rec.proficiency = new_prof
            rec.save()

        CharacterFieldNote.objects.update_or_create(
            character=character,
            key=f"skill_prof:{key}",
            defaults={"note": note},
        )

        return redirect("characters:character_detail", pk=pk)

    # ------- Handle "Save Skill Proficiencies" POST with reason required -------
    skill_prof_errors = []
    if request.method == "POST" and "save_skill_profs_submit" in request.POST and can_edit:
        to_apply = []
        for row in all_skill_rows:
            field = f"sp_{row['id_key']}"
            new_pk = request.POST.get(field)
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
    } for cf in owned_feats if cf.feat_id]

    feature_rows = []
    for cfeat in owned_features:
        label = cfeat.feature.name
        meta  = []
        if cfeat.feature.character_class_id:
            meta.append(cfeat.feature.character_class.name)
        if cfeat.subclass_id:
            meta.append(cfeat.subclass.name)
        row = {
            "ctype": ct_classfeature.id,
            "obj_id": cfeat.feature.id,
            "label": label,
            "meta":  " / ".join(m for m in meta if m) or "",
            "active": act_map.get((ct_classfeature.id, cfeat.feature.id), False),
            "note_key": f"cfeature:{cfeat.id}",
        }
        feature_rows.append(row)

    all_rows     = feat_rows + feature_rows
    active_rows  = [r for r in all_rows if r["active"]]
    passive_rows = [r for r in all_rows if not r["active"]]

    # ...after you compute prof_armor/prof_dodge/etc. and half_lvl...
    prof_weapon = prof_by_code.get("weapon", {"modifier": 0})["modifier"]
    half_weapon = hl_if_trained("weapon")

    # --- Single Spell/DC (per your rule: each class has only 1 DC) ---
    primary_cp = max(class_progress, key=lambda cp: cp.levels, default=None)
    dc_ability = None
    if primary_cp:
        # you said: only one; if data has 2, pick the first deterministically
        dc_ability = primary_cp.character_class.key_abilities.first()
    if dc_ability:
        abil_name = (dc_ability.name or "").lower()
        abil_mod  = _abil_mod(getattr(character, abil_name, 10))
        derived["spell_dc_main"] = 8 + abil_mod + prof_by_code.get("dc", {"modifier":0})["modifier"] + hl_if_trained("dc")
        derived["spell_dc_ability"] = abil_name.title()
    else:
        derived["spell_dc_main"] = 8 + prof_by_code.get("dc", {"modifier":0})["modifier"] + hl_if_trained("dc")
        derived["spell_dc_ability"] = "—"

    # --- Equip pickers (Combat tab) ---
    weapons_list = list(
        Weapon.objects.all().order_by("name").values("id","name","damage","range_type")
    )
    # currently equipped (new 3-slot system)
    by_slot = {
        e.slot_index: e
        for e in character.equipped_weapons.select_related("weapon").all()
    }

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
        math_ = _weapon_math_for(w, str_mod, dex_mod, prof_weapon, half_weapon)
        attacks_detailed.append({
            "slot": label,
            "weapon_id": w.id,
            "name": w.name,
            "damage_die": w.damage,
            "range_type": w.range_type,
            "traits": math_["traits"],
            "base": math_["base"],
            "hit_str": math_["hit_str"],
            "hit_dex": math_["hit_dex"],
            "dmg_str": math_["dmg_str"],
            "dmg_dex": math_["dmg_dex"],
            "show_choice_hit": math_["show_choice_hit"],
            "show_choice_dmg": math_["show_choice_dmg"],
            "rule": math_["rule"],
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

    # ----- Weapons (3 equipped) + math, lowercase trait matching -----
    weapons_list = list(Weapon.objects.all().order_by("name").values("id","name","damage","range_type"))
    by_slot = {e.slot_index: e for e in character.equipped_weapons.select_related("weapon").all()}

    prof_weapon = prof_by_code.get("weapon", {"modifier": 0})["modifier"]
    half_weapon = hl_if_trained("weapon")
    str_mod = _abil_mod(character.strength)
    dex_mod = _abil_mod(character.dexterity)

    attacks_detailed = []
    for slot_index, slot_label in [(1,"Primary"),(2,"Secondary"),(3,"Tertiary")]:
        rec = by_slot.get(slot_index)
        if not rec: 
            continue
        w   = rec.weapon
        m   = _weapon_math(w, str_mod, dex_mod, prof_weapon, half_weapon)
        attacks_detailed.append({
            "slot": slot_label,
            "weapon_id": w.id,
            "name": w.name,
            "damage_die": w.damage,
            "range_type": w.range_type,
            **m
        })

    # ----- Tabs payloads -----
    # Details: placeholders now, fill later in your editor
    details_placeholders = {
        "appearance": character.backstory[:200] if character.backstory else "",
        "hooks": "",
        "notes": "",
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
            "weapons": attacks_detailed,  # contains hit_str/hit_dex/dmg_str/dmg_dex + flags
        }
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
        "actions_text": True,  # tell template to show the long combat-actions section below
    }

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

    # ── 6) RENDER character_detail.html ───────────────────────────────────
    return render(request, 'forge/character_detail.html', {
        'character':          character,
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
        
        'auto_feats':         auto_feats,
        'form':               level_form,
        'edit_form':          edit_form,
    'feature_fields':         feature_fields,
    'spellcasting_blocks': spellcasting_blocks,
    'subclass_feats_at_next': subclass_feats_at_next,
            'proficiency_rows':   proficiency_rows,   # (preview table you already had)
        'proficiency_summary': proficiency_summary,
        'manual_form': manual_form,
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


    })
from django.views.decorators.http import require_POST


@login_required
@require_POST
def set_field_override(request, pk):
    character = get_object_or_404(Character, pk=pk, user=request.user)
    key   = (request.POST.get("key") or "").strip()
    value = (request.POST.get("value") or "").strip()
    note  = (request.POST.get("note") or "").strip()
    if not note:
        return HttpResponseBadRequest("A reason is required for this change.")  # ← enforce

    if value == "":
        CharacterFieldOverride.objects.filter(character=character, key=key).delete()
    else:
        CharacterFieldOverride.objects.update_or_create(
            character=character, key=key, defaults={"value": value}
        )

    CharacterFieldNote.objects.update_or_create(
        character=character, key=key, defaults={"note": note}
    )
    return JsonResponse({"ok": True})


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
