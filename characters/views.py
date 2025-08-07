from django.shortcuts import render

# Create your views here.
# characters/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django_select2.views import AutoResponseView

from .models import Character
from campaigns.models import Campaign

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

def class_list(request):
    classes = CharacterClass.objects.all().order_by('name')
    return render(request, 'codex/class_list.html', {'classes': classes})



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
from django.db.models import Q
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
                    subskill = SubSkill.objects.get(name=subname, category__name=category)
                    prof     = ProficiencyLevel.objects.get(name__iexact=tier_name)
                    CharacterSkillProficiency.objects.create(
                        character=character,
                        subskill=subskill,
                        proficiency=prof
                    )
            except (ValueError, SubSkill.DoesNotExist, ProficiencyLevel.DoesNotExist):
                # ignore any parse/look-up errors
                pass

            return redirect('characters:character_list', pk=character.pk)

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
    selected_pk = request.GET.get('base_class')
    if selected_pk and selected_pk.isdigit():
        preview_cls = CharacterClass.objects.get(pk=selected_pk)
    else:
        preview_cls = default_cls
    subclass_groups = (
        preview_cls.subclass_groups
                   .order_by('name')
                   .prefetch_related('subclasses')
    )
    # pull the ClassLevel & its features for preview_cls@next_level
    try:
        cl = ClassLevel.objects.get(character_class=preview_cls, level=next_level)
        base_feats = list(cl.features.all())
    except ClassLevel.DoesNotExist:
        base_feats = []

    # which feature‐objects are auto‐granted
    auto_feats = [
        f for f in base_feats
        if isinstance(f, ClassFeature) and f.scope in ('class_feat','subclass_feat')
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
        uni=uni
    )

    if request.method == 'POST' and 'level_up_submit' in request.POST and level_form.is_valid():
        # ... your existing POST handler ...

        # A) update ClassProgress
        picked_cls = level_form.cleaned_data['base_class']
        if total_level == 0:
            cp = CharacterClassProgress.objects.create(
                character=character,
                character_class=picked_cls,
                levels=1
            )
        else:
            cp = CharacterClassProgress.objects.get(
                character=character,
                character_class=picked_cls
            )
            cp.levels += 1
            cp.save()

        # B) bump character level
        character.level = next_level
        character.save()

        # C) grant auto feats
        for feat in level_form.auto_feats:
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

        # E) subclass choices & feature options
        for name, val in level_form.cleaned_data.items():
            if name.startswith('feat_') and val:
                feat_pk = int(name.split('_')[1])
                cf      = ClassFeature.objects.get(pk=feat_pk)
                if name.endswith('_subclass'):
                    sub = cf.subclass_group.subclasses.get(pk=int(val))
                    CharacterFeature.objects.create(
                        character=character,
                        feature=cf,
                        subclass=sub,
                        level=next_level
                    )
                elif name.endswith('_option'):
                    opt = cf.options.get(pk=int(val))
                    CharacterFeature.objects.create(
                        character=character,
                        feature=cf,
                        option=opt,
                        level=next_level
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
    feature_fields = []
    for feat in to_choose:
        if isinstance(feat, ClassFeature) and feat.scope == 'subclass_choice':
            fn = f"feat_{feat.pk}_subclass"
            feature_fields.append((level_form[fn], f"Choose {feat.subclass_group.name}"))
        elif isinstance(feat, ClassFeature) and feat.has_options:
            fn = f"feat_{feat.pk}_option"
            feature_fields.append((level_form[fn], feat.name))


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
        'feature_fields':     feature_fields,
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

@login_required
def level_down(request, pk):
    character = get_object_or_404(Character, pk=pk, user=request.user)
    if character.level > 0:
        lvl = character.level
        # remove all features from that level
        character.features.filter(level=lvl).delete()

        # decrement most‐recent class_progress
        cp = character.class_progress.order_by('-levels').first()
        if cp and cp.levels >= lvl:
            cp.levels -= 1
            if cp.levels == 0:
                cp.delete()
            else:
                cp.save()

        # bump charset level down
        character.level = lvl - 1
        character.save()

    return redirect('character_detail', pk=pk)
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
