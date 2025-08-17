from django.shortcuts import render

# Create your views here.
# characters/views.py
from django.db.models import Q, Max
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django_select2.views import AutoResponseView
from django.db.models import Count
from .models import Character
from campaigns.models import Campaign
from django.db import models

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
from .forms import CharacterCreationForm
import re
from django.views.generic import ListView, DetailView
# views.py
import json
from django.shortcuts import render, redirect
from .forms import CharacterCreationForm

# characters/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import CharacterCreationForm
from .models import Character, CharacterFeat
from .models import SubSkill, ProficiencyLevel, CharacterSkillProficiency

from django.shortcuts import render
from characters.models import LoremasterArticle,Spell,Subrace, CharacterFeature, ClassFeat,UniversalLevelFeature, CharacterClass, ClassFeature, ClassSubclass, SubclassGroup
def _class_level_after_pick(character, base_class):
    """Class-level for the selected class *after* this level-up."""
    prog = character.class_progress.filter(character_class=base_class).first()
    return (prog.levels if prog else 0) + 1
LEVEL_NUM_RE = re.compile(r'(\d+)\s*(?:st|nd|rd|th)?')

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

@login_required
def level_down(request, pk):
    character = get_object_or_404(Character, pk=pk, user=request.user)
    if character.level > 0:
        lvl = character.level
        # 1) remove all features gained at that level
        character.features.filter(level=lvl).delete()

        # 2) find the class-progress entry that just gained this level
        cp = character.class_progress.filter(levels__gte=lvl).order_by('-levels').first()
        if cp:
            cp.levels -= 1
            if cp.levels <= 0:
                cp.delete()
            else:
                cp.save()

        # 3) decrement overall level
        character.level = lvl - 1
        character.save()

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

    subclass_groups = (
        preview_cls.subclass_groups
                .order_by('name')
                .prefetch_related('subclasses', 'tier_levels')  # ← add 'tier_levels'
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



    # which feature‐objects are auto‐granted
    auto_feats = [
        f for f in base_feats
        if isinstance(f, ClassFeature) and f.scope == 'class_feat'
    ]

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
                    .filter(
                        scope='subclass_feat',
                        subclass_group=grp,
                        subclasses=sub,
                    )
                    .filter(Q(tier__in=unlock_tiers) | Q(tier__isnull=True))
                    .filter(Q(level_required__isnull=True) | Q(level_required__lte=cls_level_after))
                    .filter(Q(min_level__isnull=True)    | Q(min_level__lte=cls_level_after))
                    .exclude(pk__in=taken_feature_ids)
                )
                for f in base:
                    # T1 always OK; T>1 requires T-1 from the same subclass
                    if not f.tier or f.tier == 1 or ((f.tier - 1) in prev_tiers_by_sub.get(sub.pk, set())):
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

            auto_feats_post = [f for f in cl_next.features.all() if f.scope == 'class_feat']
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
        if level_form.cleaned_data.get('asi'):
            CharacterFeature.objects.create(
                character=character,
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

                        if unlock_tiers:
                            grant_feats = list(
                                ClassFeature.objects.filter(
                                    scope='subclass_feat',
                                    subclass_group=grp,
                                    subclasses=sub,
                                    tier__in=unlock_tiers
                                )
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

        return redirect('characters:character_detail', pk=pk)

    # ── 5) BUILD feature_fields FOR TEMPLATE ───────────────────────────────
    subclass_feats_at_next = {}
    for grp in subclass_groups:
        # If modular-linear, figure out which tiers unlock at this level
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
                # DB filter by tiers that unlock now
                qs = qs.filter(tier__in=unlock_tiers) if unlock_tiers else qs.none()
                feats = list(qs.order_by('name'))
            else:
                # LINEAR: pull directly from features already on this class level
                feats = [
                    f for f in base_feats
                    if f.scope == 'subclass_feat'
                    and f.subclass_group_id == grp.id
                    and sc in f.subclasses.all()
                ]
                feats.sort(key=lambda f: f.name)

            if feats:
                subclass_feats_at_next[sc.pk] = feats


    for feat in to_choose:
        if isinstance(feat, ClassFeature) and feat.scope == 'subclass_choice':
            fn  = f"feat_{feat.pk}_subclass"
            grp = feat.subclass_group
            feature_fields.append({
                "kind":  "subclass_choice",
                "label": f"Choose {grp.name}",
                "field": level_form[fn],
                "group": grp,
            })
        elif isinstance(feat, ClassFeature) and feat.has_options:
            fn = f"feat_{feat.pk}_option"
            feature_fields.append({
                "kind":  "option",
                "label": feat.name,
                "field": level_form[fn],
                "feature": feat,  
            })
               


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
        'proficiency_rows':   proficiency_rows,
        'auto_feats':         auto_feats,
        'form':               level_form,
        'edit_form':          edit_form,
    'feature_fields':         feature_fields,
    'subclass_feats_at_next': subclass_feats_at_next,
    

    })
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
