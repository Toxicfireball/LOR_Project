# campaigns/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, Http404
from django.contrib import messages
from characters.models import Character

from .models import Campaign, CampaignMembership
from .forms import CampaignCreationForm, AttachCharacterForm
from characters.models import Character

def _is_gm(user, campaign: Campaign) -> bool:
    return CampaignMembership.objects.filter(
        campaign=campaign, user=user, role="gm"
    ).exists()

@login_required
def campaign_list(request):
    # You can change to only show the user's campaigns if you prefer
    campaigns = Campaign.objects.all().order_by("-created_at")
    return render(request, "campaigns/campaign_list.html", {"campaigns": campaigns})

@login_required
def campaign_detail(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    is_member = campaign.members.filter(id=request.user.id).exists()
    is_gm = _is_gm(request.user, campaign)

    memberships = (campaign.campaignmembership_set
                   .select_related("user")
                   .order_by("role", "user__username"))

    # GM sees all characters; players see only their own
    if is_gm:
        attached_characters = (campaign.characters
                               .select_related("user")
                               .order_by("user__username", "name"))
    else:
        attached_characters = (campaign.characters
                               .filter(user=request.user)
                               .select_related("user")
                               .order_by("name"))

    stats = {
        "gm_count": memberships.filter(role="gm").count(),
        "player_count": memberships.filter(role="pc").count(),
        "char_count": campaign.characters.count(),
    }

    # ⬇️ DO **NOT** do character-level permission checks here.
    # That belongs in characters.views.character_detail.

    attach_form = AttachCharacterForm(user=request.user, campaign=campaign, is_gm=is_gm)

    context = {
        "campaign": campaign,
        "memberships": memberships,
        "is_member": is_member,
        "is_gm": is_gm,
        "attached_characters": attached_characters,
        "attach_form": attach_form,
        "stats": stats,
    }
    return render(request, "campaigns/campaign_detail.html", context)

@login_required
def join_campaign(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if not CampaignMembership.objects.filter(user=request.user, campaign=campaign).exists():
        CampaignMembership.objects.create(user=request.user, campaign=campaign, role="pc")
        messages.success(request, "Joined campaign as a player.")
    else:
        messages.info(request, "You’re already a member of this campaign.")

    return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

@login_required
def create_campaign(request):
    if request.method == "POST":
        form = CampaignCreationForm(request.POST)
        if form.is_valid():
            campaign = form.save()
            CampaignMembership.objects.create(user=request.user, campaign=campaign, role="gm")
            messages.success(request, "Campaign created. You’re the GM!")
            return redirect("campaigns:campaign_detail", campaign_id=campaign.id)
    else:
        form = CampaignCreationForm()
    return render(request, "campaigns/create_campaign.html", {"form": form})

@login_required
def attach_character(request, campaign_id):
    if request.method != "POST":
        raise Http404()
    campaign = get_object_or_404(Campaign, id=campaign_id)
    is_gm = _is_gm(request.user, campaign)

    form = AttachCharacterForm(request.POST, user=request.user, campaign=campaign, is_gm=is_gm)
    if not form.is_valid():
        messages.error(request, "Please pick a character.")
        return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

    character: Character = form.cleaned_data["character"]

    # Permission: owner can attach their own; GM can attach anyone.
    if not (is_gm or character.user_id == request.user.id):
        return HttpResponseForbidden("You can only attach your own characters.")

    character.campaign = campaign
    character.save()

    # Ensure the character’s owner is a member (auto-add as player if needed)
    CampaignMembership.objects.get_or_create(
        campaign=campaign,
        user=character.user,
        defaults={"role": "pc"},
    )

    messages.success(request, f"Attached {character.name} to {campaign.name}.")
    return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

@login_required
def detach_character(request, campaign_id, character_id):
    if request.method != "POST":
        raise Http404()
    campaign = get_object_or_404(Campaign, id=campaign_id)
    character = get_object_or_404(Character, id=character_id)

    is_gm = _is_gm(request.user, campaign)
    if not (is_gm or character.user_id == request.user.id):
        return HttpResponseForbidden("You can only detach your own characters.")

    if character.campaign_id != campaign.id:
        messages.info(request, "That character isn’t attached to this campaign.")
        return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

    character.campaign = None
    character.save()
    messages.success(request, f"Detached {character.name} from {campaign.name}.")
    return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

@login_required
def leave_campaign(request, campaign_id):
    """Player leaves the campaign; any of their characters attached are auto-detached.
       (GM should reassign GM role first if they’re the only GM.)"""
    campaign = get_object_or_404(Campaign, id=campaign_id)

    try:
        membership = CampaignMembership.objects.get(campaign=campaign, user=request.user)
    except CampaignMembership.DoesNotExist:
        messages.info(request, "You’re not in this campaign.")
        return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

    if membership.role == "gm":
        # Safety guard; tweak policy as you like
        other_gms = CampaignMembership.objects.filter(campaign=campaign, role="gm").exclude(user=request.user).exists()
        if not other_gms:
            messages.error(request, "You’re the only GM. Add another GM before leaving.")
            return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

    # Detach all of this user’s characters from this campaign
    Character.objects.filter(user=request.user, campaign=campaign).update(campaign=None)
    membership.delete()
    messages.success(request, "You left the campaign.")
    return redirect("campaigns:campaign_list")
