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
    return render(request, 'characters/character_list.html', {'characters': characters})


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
from characters.models import Spell, ClassFeat, CharacterClass, ClassFeature, ClassSubclass, SubclassGroup



from django.shortcuts import render
from .models import Spell

from django.shortcuts import render
from .models import Spell

from django.shortcuts import render
from .models import Spell

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



def class_subclass_list(request):
    subclasses = ClassSubclass.objects.select_related('base_class').order_by('base_class__name', 'name')
    return render(request, 'codex/subclasses.html', {'subclasses': subclasses})

def subclass_group_list(request):
    groups = SubclassGroup.objects.select_related('character_class').order_by('character_class__name', 'name')
    return render(request, 'codex/groups.html', {'groups': groups})


from characters.models import CharacterClass, ClassFeature, ClassSubclass, SubclassGroup, ClassLevel

def class_detail(request, pk):
    cls = get_object_or_404(CharacterClass, pk=pk)
    features = ClassFeature.objects.filter(character_class=cls).order_by('name')
    subclasses = ClassSubclass.objects.filter(base_class=cls).order_by('name')
    levels = ClassLevel.objects.filter(character_class=cls).prefetch_related('features').order_by('level')

    return render(request, 'codex/class_detail.html', {
        'cls': cls,
        'features': features,
        'subclasses': subclasses,
        'levels': levels,
    })


@login_required
def create_character(request):
    if request.method == 'POST':
        # Make a mutable copy of the POST data
        post_data = request.POST.copy()
        
        # If the side_background_2 field is missing (due to the missing name attribute in HTML),
        # add it as an empty string.
        if 'side_background_2' not in post_data:
            post_data['side_background_2'] = ''
        
        # Instantiate the form with the modified POST data
        form = CharacterCreationForm(post_data)
        
        if form.is_valid():
            character = form.save(commit=False)
            character.user = request.user
            character.save()
            raw_profs = request.POST.get('computed_skill_proficiencies')
            if raw_profs:
                    try:
                        prof_data = json.loads(raw_profs)
                        for name, prof in prof_data.items():
                            category_name, subskill_name = name.split(" - ", 1)
                            sub = SubSkill.objects.get(name=subskill_name, category__name=category_name)
                            prof_lvl = ProficiencyLevel.objects.get(name=prof)
                            CharacterSkillProficiency.objects.create(character=character, subskill=sub, proficiency=prof_lvl)
                    except Exception as e:
                        print("Skill parsing failed:", e)
                    return redirect('character_detail', pk=character.pk)
        else:
            print("Form errors:", form.errors)
    else:
        form = CharacterCreationForm()
    
    return render(request, 'characters/create_character.html', {'form': form})



@login_required
def character_detail(request, pk):
    # Ensure that the character belongs to the current user.
    character = get_object_or_404(Character, pk=pk, user=request.user)
    return render(request, 'characters/character_detail.html', {'character': character})


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Character, CharacterClass, ClassLevel, CharacterClassProgress
from .forms import LevelUpForm

@login_required
def level_up(request, char_id):
    character = get_object_or_404(Character, id=char_id, user=request.user)
    form = LevelUpForm(request.POST or None, character=character)

    # Determine default preview of next level features
    if character.level == 0:
        default_class = CharacterClass.objects.first()
        next_lvl = 1
    else:
        first_prog = character.class_progress.first()
        if first_prog:
            default_class = first_prog.character_class
            next_lvl = first_prog.levels + 1
        else:
            default_class = None
            next_lvl = None
    preview_features = []
    if default_class and next_lvl:
        try:
            cl = ClassLevel.objects.get(character_class=default_class, level=next_lvl)
            preview_features = cl.features
        except ClassLevel.DoesNotExist:
            preview_features = []

    # Map feature tags to option lists when applicable
    feature_options = {
        'WZ11A': [
            'Abjuration','Conjuration','Divination','Enchantment','Evocation',
            'Illusion','Necromancy','Transmutation','War Magic','Biomancy',
            'Chronology','Psionics','Elemental Magic','Battle Mages'
        ]
    }

    # Handle form submission
    if request.method == 'POST' and form.is_valid():
        # First level assignment
        if character.level == 0 and form.cleaned_data['base_class']:
            cls = form.cleaned_data['base_class']
            progress = CharacterClassProgress.objects.create(
                character=character,
                character_class=cls,
                levels=1
            )
            cl = ClassLevel.objects.get(character_class=cls, level=1)
            # TODO: apply cl.proficiency_tier & cl.features to character
            character.level = 1
            character.save()
        # Adding a level to existing class
        elif form.cleaned_data['advance_class']:
            cls = form.cleaned_data['advance_class']
            progress = CharacterClassProgress.objects.get(
                character=character, character_class=cls
            )
            new_level = progress.levels + 1
            cl = ClassLevel.objects.get(character_class=cls, level=new_level)
            # TODO: apply cl.proficiency_tier & cl.features to character
            progress.levels = new_level
            progress.save()
            character.level += 1
            character.save()
        return redirect('characters:character_detail', pk=character.pk)

    context = {
        'character': character,
        'form': form,
        'total_level': character.level,
        'class_breakdown': character.class_progress.all(),
        'preview_features': preview_features,
        'feature_options': feature_options,
    }
    return render(request, 'characters/level_up.html', context)