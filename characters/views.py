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
from characters.models import Spell, ClassFeat


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

    return render(request, 'characters/spell_list.html', {
        'spells': spells,
        'levels': levels,
        'origins': origins,
        'classifications': classifications,
        'query': query,
        'selected_level': level,
    })




def feat_list(request):
    feats = ClassFeat.objects.all()

    query = request.GET.get('q')
    if query:
        feats = feats.filter(name__icontains=query) | feats.filter(tags__icontains=query)

    feat_type = request.GET.get('type')
    if feat_type:
        feats = feats.filter(feat_type__icontains=feat_type)

    feats = feats.order_by('name')

    # Tabs
    types = sorted(set(feats.values_list('feat_type', flat=True)))

    # Dropdown filter (individual feat types split from combo strings)
    raw_feat_types = feats.values_list('feat_type', flat=True)
    feat_types = sorted({ft.strip() for val in raw_feat_types for ft in val.split(',') if ft.strip()})

    return render(request, 'characters/feat_list.html', {
        'feats': feats,
        'types': types,
        'feat_types': feat_types,  # ✅ new for filter dropdown
        'query': query,
        'selected_type': feat_type,
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
def character_list(request):
    characters = request.user.characters.all()
    return render(request, 'characters/character_list.html', {'characters': characters})

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