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
