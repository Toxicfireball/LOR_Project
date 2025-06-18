from django.shortcuts import render

# Create your views here.
# characters/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

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
from .models import Character
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
    for group in subclass_groups:
        for sub in group.subclasses.all():
            fbylevel = {}
            for cl in levels:
                # pick only the features you inlined AND that list this sub
                feats = [
                    f for f in cl.features.all()
                    if f.scope == 'subclass_feat' and sub in f.subclasses.all()
                ]
                if feats:
                    fbylevel[cl.level] = feats
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

class RulebookListView(ListView):
    model = Rulebook
    template_name = "rulebook/list.html"       # ← match your folder name
    context_object_name = "rulebooks"
    paginate_by = 10                             # ← show 10 per page

    def get_queryset(self):
        qs = super().get_queryset()
        q  = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs.order_by("name")


class RulebookDetailView(DetailView):
    model = Rulebook
    template_name = "rulebook/detail.html"
    context_object_name = "rulebook"

class RulebookPageDetailView(DetailView):
    model = RulebookPage
    template_name = "rulebook/page_detail.html"
    context_object_name = "page"

@login_required
def create_character(request):
    """
    Stage 1: Name, race, subrace, backgrounds, ability scores, backstory, and computed skill proficiencies.
    """
    if request.method == 'POST':
        form = CharacterCreationForm(request.POST)
        if form.is_valid():
            # save Character
            character = form.save(commit=False)
            character.user = request.user
            character.save()

            # parse and save computed skill proficiencies
            raw = form.cleaned_data.get('computed_skill_proficiencies') or '{}'
            try:
                prof_map = json.loads(raw)
                for full_name, tier_name in prof_map.items():
                    # full_name like "Athletics – Climbing"
                    cat, sub = full_name.split(' – ', 1)
                    subskill = SubSkill.objects.get(name=sub, category__name=cat)
                    prof     = ProficiencyLevel.objects.get(name__iexact=tier_name)
                    CharacterSkillProficiency.objects.create(
                        character=character,
                        subskill=subskill,
                        proficiency=prof
                    )
            except Exception:
                # silently ignore parse errors
                pass

            return redirect('character_detail', pk=character.pk)
    else:
        form = CharacterCreationForm()

    # prepare JSON for frontend
    races = []
    for r in Race.objects.prefetch_related('subraces').all():
        races.append({
            'code':     r.code,
            'name':     r.name,
            'mods': {
                'Strength':     r.strength_bonus,
                'Dexterity':    r.dexterity_bonus,
                'Constitution': r.constitution_bonus,
                'Intelligence': r.intelligence_bonus,
                'Wisdom':       r.wisdom_bonus,
                'Charisma':     r.charisma_bonus,
            },
            'subraces': [
                {'code': s.code, 'name': s.name}
                for s in r.subraces.all()
            ]
        })

    backgrounds = []
    for b in Background.objects.all():
        backgrounds.append({
            'code': b.code,
            'name': b.name,
            'primary': {
                'ability': b.primary_ability.name,
                'bonus':   b.primary_bonus,
                'skill':   b.primary_skill.name,
            },
            'secondary': {
                'ability': b.secondary_ability.name,
                'bonus':   b.secondary_bonus,
                'skill':   b.secondary_skill.name,
            }
        })

    context = {
        'form':             form,
        'races_json':       json.dumps(races,       cls=DjangoJSONEncoder),
        'backgrounds_json': json.dumps(backgrounds, cls=DjangoJSONEncoder),
    }
    return render(request, 'forge/create_character.html', context)


@login_required
def character_detail(request, pk):
    """
    Display a character’s full data after creation.
    """
    character = get_object_or_404(request.user.characters.select_related(
        'race', 'subrace', 'campaign'
    ), pk=pk)

    # collect skill proficiencies
    skills = character.skill_proficiencies.select_related(
        'subskill__category', 'proficiency'
    ).order_by('subskill__category__name', 'subskill__name')

    context = {
        'character': character,
        'skills':     skills,
    }
    return render(request, 'forge/character_detail.html', context)




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
    # ── 1) load the character ────────────────────────────────────────────────
    character = get_object_or_404(Character, pk=pk)
    # only the owner may edit
    can_edit = request.user == character.user

    # ── 2) build read-only context for the sheet ─────────────────────────────
    ability_map = {
        'Strength':     character.strength,
        'Dexterity':    character.dexterity,
        'Constitution': character.constitution,
        'Intelligence': character.intelligence,
        'Wisdom':       character.wisdom,
        'Charisma':     character.charisma,
    }
    skill_proficiencies = character.skill_proficiencies.all()
    class_progress      = character.class_progress.select_related('character_class')
    racial_features     = character.race.features.all() if character.race else []
    universal_feats     = UniversalLevelFeature.objects.filter(level=character.level)
    total_level         = character.level

    # ── 3) prepare level-up preview (next level) ────────────────────────────
    next_level = total_level + 1
    # pick which class is being leveled for preview
    first_prog = character.class_progress.first()
    preview_class = first_prog.character_class if first_prog else CharacterClass.objects.first()
    try:
        cl = ClassLevel.objects.get(character_class=preview_class, level=next_level)
        base_feats = list(cl.features.all())
    except ClassLevel.DoesNotExist:
        base_feats = []

    uni = UniversalLevelFeature.objects.filter(level=next_level).first()
    to_choose = base_feats.copy()
    if uni:
        if uni.grants_general_feat: to_choose.append("general_feat")
        if uni.grants_asi:           to_choose.append("asi")

    # ── 4) handle POST of **either** the edit form or the level-up form ──────
    edit_form  = None
    level_form = None

    if request.method == 'POST':
        # bind both forms
        if can_edit:
            edit_form = CharacterCreationForm(request.POST, instance=character)
        level_form = LevelUpForm(request.POST, character=character, to_choose=to_choose, uni=uni)

        # a) edit form submitted?
        if can_edit and 'edit_submit' in request.POST and edit_form.is_valid():
            edit_form.save()
            return redirect('characters:character_detail', pk=pk)

        # b) level up form submitted?
        if level_form.is_valid() and 'level_up_submit' in request.POST:
            # 1) figure out which class they picked
            picked_base    = level_form.cleaned_data.get('base_class')
            picked_advance = level_form.cleaned_data.get('advance_class')
            picked_cls     = picked_base or picked_advance

            # 2) update CharacterClassProgress
            if total_level == 0:
                prog = CharacterClassProgress.objects.create(
                    character=character,
                    character_class=picked_cls,
                    levels=1
                )
            else:
                prog = CharacterClassProgress.objects.get(
                    character=character,
                    character_class=picked_cls
                )
                prog.levels += 1
                prog.save()

            # 3) bump character level
            character.level = next_level
            character.save()

            # 4) re-grant the features exactly as you had in level_up()
            cl = ClassLevel.objects.get(character_class=picked_cls, level=next_level)
            to_grant = list(cl.features.all())
            uni2     = UniversalLevelFeature.objects.filter(level=next_level).first()
            if uni2 and uni2.grants_general_feat: to_grant.append("general_feat")
            if uni2 and uni2.grants_asi:           to_grant.append("asi")

            for feat in to_grant:
                # … same loops you already wrote to create CharacterFeature entries …
                # for brevity, I’m omitting that here
                pass

            return redirect('characters:character_detail', pk=pk)

    else:
        # GET: unbound forms
        if can_edit:
            edit_form = CharacterCreationForm(instance=character)
        level_form = LevelUpForm(character=character, to_choose=to_choose, uni=uni)

    # ── 5) build a simple list of (BoundField, label) for your template ──────
    feature_fields = []
    for feat in to_choose:

        
        if feat == "general_feat":
            feature_fields.append((level_form['general_feat'], "General Feat"))
        elif feat == "asi":
            feature_fields.append((level_form['asi'], "Ability Score Increase"))
        elif hasattr(feat, 'scope') and feat.scope == "subclass_choice":
            fn = f"feat_{feat.pk}_subclass"
            feature_fields.append((level_form[fn], f"Choose {feat.subclass_group.name}"))
        elif hasattr(feat, 'has_options') and feat.has_options:
            fn = f"feat_{feat.pk}_option"
            feature_fields.append((level_form[fn], feat.name))
        else:
            fn = f"feat_{feat.pk}"
            feature_fields.append((level_form[fn], feat.name))
    subrace_name = None
    if character.subrace_id:
        subrace = Subrace.objects.filter(pk=character.subrace_id).first()
        subrace_name = subrace.name if subrace else None
    # ── 6) render everything in one template ─────────────────────────────────
    return render(request, 'characters/character_detail.html', {
        'character':           character,
        'can_edit':            can_edit,
        'subrace_name':        subrace_name,      # ← new
        'ability_map':         ability_map,
        'skill_proficiencies': skill_proficiencies,
        'class_progress':      class_progress,
        'racial_features':     racial_features,
        'universal_feats':     universal_feats,
        'total_level':         total_level,
        'edit_form':           edit_form,
        'form':                level_form,
        'feature_fields':      feature_fields,
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import (
    Character, CharacterClassProgress, ClassLevel, UniversalLevelFeature,
    CharacterFeature, ClassFeature, ClassSubclass, FeatureOption
)
from .forms import LevelUpForm

@login_required
def level_up(request, char_id):
    character  = get_object_or_404(Character, id=char_id, user=request.user)
    next_level = character.level + 1

    # 1) Pick which class we’re leveling
    if request.method == 'POST':
        cls = None   # we’ll set this after form.is_valid()
    else:
        prog = character.class_progress.first()
        cls  = prog.character_class if prog else CharacterClass.objects.first()

    # 2) Compute which features to choose at this level
    try:
        cl          = ClassLevel.objects.get(character_class=cls, level=next_level)
        base_feats  = list(cl.features.all())
    except ClassLevel.DoesNotExist:
        base_feats = []

    uni       = UniversalLevelFeature.objects.filter(level=next_level).first()
    to_choose = base_feats.copy()
    if uni:
        if uni.grants_general_feat: to_choose.append("general_feat")
        if uni.grants_asi:           to_choose.append("asi")

    # 3) Instantiate the form with those choices
    form = LevelUpForm(
        request.POST or None,
        character=character,
        to_choose=to_choose,
        uni=uni
    )

    feature_fields = []
    if request.method == 'POST' and form.is_valid():
        # 4) Determine picked class
        cls = form.cleaned_data.get('base_class') or form.cleaned_data.get('advance_class')

        # 5) Update/create class progress
        if character.level == 0:
            CharacterClassProgress.objects.create(character=character, character_class=cls, levels=1)
        else:
            prog = CharacterClassProgress.objects.get(character=character, character_class=cls)
            prog.levels += 1
            prog.save()

        # 6) Bump total level
        character.level = next_level
        character.save()

        # 7) Persist each feature the user ticked/chose
        #    (We rebuild to_choose here to match the form’s fields exactly)
        cl         = ClassLevel.objects.get(character_class=cls, level=next_level)
        base_feats = list(cl.features.all())
        uni        = UniversalLevelFeature.objects.filter(level=next_level).first()
        to_choose  = base_feats.copy()
        if uni:
            if uni.grants_general_feat: to_choose.append("general_feat")
            if uni.grants_asi:           to_choose.append("asi")

        for feat in to_choose:
            # General Feat
            if feat == "general_feat" and form.cleaned_data.get('general_feat'):
                CharacterFeature.objects.create(character=character, level=next_level)
                continue
            # ASI
            if feat == "asi" and form.cleaned_data.get('asi'):
                CharacterFeature.objects.create(character=character, level=next_level)
                continue
            # Subclass Choice
            if isinstance(feat, ClassFeature) and feat.scope == "subclass_choice":
                fname = f"feat_{feat.pk}_subclass"
                sub_id = form.cleaned_data.get(fname)
                if sub_id:
                    sub = ClassSubclass.objects.get(pk=sub_id)
                    CharacterFeature.objects.create(
                        character=character, feature=feat, subclass=sub, level=next_level
                    )
                continue
            # Options
            if isinstance(feat, ClassFeature) and feat.has_options:
                fname = f"feat_{feat.pk}_option"
                opt_id = form.cleaned_data.get(fname)
                if opt_id:
                    opt = FeatureOption.objects.get(pk=opt_id)
                    CharacterFeature.objects.create(
                        character=character, feature=feat, option=opt, level=next_level
                    )
                continue
            # Plain tickbox
            if isinstance(feat, ClassFeature):
                fname = f"feat_{feat.pk}"
                if form.cleaned_data.get(fname):
                    CharacterFeature.objects.create(
                        character=character, feature=feat, level=next_level
                    )
        return redirect('characters:character_detail', pk=character.pk)

    # 8) Build a list of BoundFields + labels for the template
    for feat in to_choose:
        if feat == "general_feat" and 'general_feat' in form.fields:
            feature_fields.append((form['general_feat'], "General Feat"))
            continue
        if feat == "asi" and 'asi' in form.fields:
            feature_fields.append((form['asi'], "Ability Score Increase"))
            continue
        if isinstance(feat, ClassFeature) and feat.scope == "subclass_choice":
            fname = f"feat_{feat.pk}_subclass"
            if fname in form.fields:
                feature_fields.append((form[fname], f"Choose your {feat.subclass_group.name}"))
            continue
        if isinstance(feat, ClassFeature) and feat.has_options:
            fname = f"feat_{feat.pk}_option"
            if fname in form.fields:
                feature_fields.append((form[fname], feat.name))
            continue
        if isinstance(feat, ClassFeature):
            fname = f"feat_{feat.pk}"
            if fname in form.fields:
                feature_fields.append((form[fname], feat.name))

    return render(request, 'characters/forge/level_up.html', {
        'character':      character,
        'form':           form,
        'total_level':    character.level,
        'feature_fields': feature_fields,
    })


