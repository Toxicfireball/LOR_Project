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
from .forms import CharacterCreationStage1Form

@login_required
def create_character_stage1(request):
    if request.method == 'POST':
        form = CharacterCreationStage1Form(request.POST)
        if form.is_valid():
            character = form.save(commit=False)
            character.user = request.user
            character.level = 0  # Character is created at level 0 in Stage 1
            character.save()
            # Redirect to the dashboard or home page that shows all characters/campaigns
            return redirect('home')
    else:
        form = CharacterCreationStage1Form()
    return render(request, 'characters/create_character_stage1.html', {'form': form})
