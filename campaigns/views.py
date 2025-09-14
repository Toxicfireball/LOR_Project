# campaigns/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, Http404
from django.contrib import messages
from characters.models import Character
from django.urls import reverse

@login_required
def send_campaign_message(request, campaign_id):
    if request.method != "POST":
        raise Http404()
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if not campaign.members.filter(id=request.user.id).exists():
        return HttpResponseForbidden("Join the campaign first.")

    form = MessageForm(request.POST, campaign=campaign, user=request.user)
    if not form.is_valid():
        messages.error(request, "Please select a recipient and enter a message.")
        return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#messages")

    msg = CampaignMessage.objects.create(
        campaign=campaign,
        sender=request.user,
        recipient=form.cleaned_data["recipient"],
        content=form.cleaned_data["content"],
    )
    messages.success(request, "Message sent.")
    return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#messages")

from .models import Campaign, CampaignMembership
from .forms import CampaignCreationForm, AttachCharacterForm
from characters.models import Character
# BEFORE imports
# from .models import Campaign, CampaignMembership
# from .forms import CampaignCreationForm, AttachCharacterForm
# AFTER imports
from .models import Campaign, CampaignMembership, CampaignNote, PartyItem, CampaignMessage
from .forms import (
    CampaignCreationForm, AttachCharacterForm,
    JoinCampaignForm, CampaignNoteForm, MessageForm
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch, Q, Count

def _is_gm(user, campaign: Campaign) -> bool:
    return CampaignMembership.objects.filter(
        campaign=campaign, user=user, role="gm"
    ).exists()

@login_required
def campaign_list(request):
    # You can change to only show the user's campaigns if you prefer
    campaigns = Campaign.objects.all().order_by("-created_at")
    return render(request, "campaigns/campaign_list.html", {"campaigns": campaigns})

# campaign_detail — AFTER (add extra context)

from django.db.models import Q
from django.contrib import messages
from .forms import CampaignCreationForm, AttachCharacterForm, CampaignNoteForm, PartyItemForm, MessageForm, JoinCampaignForm
from .models import Campaign, CampaignMembership, CampaignNote, PartyItem, CampaignMessage

@login_required
def campaign_detail(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    is_member = campaign.members.filter(id=request.user.id).exists()
    is_gm = _is_gm(request.user, campaign)

    memberships = (campaign.campaignmembership_set
                   .select_related("user")
                   .order_by("role", "user__username"))

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
    attach_form = AttachCharacterForm(user=request.user)
    # Members + their chars for display
    chars_by_user = {}
    for ch in campaign.characters.select_related("user").only("id", "name", "user_id"):
        chars_by_user.setdefault(ch.user_id, []).append(ch)
    memberships_with_chars = [{"m": m, "chars": chars_by_user.get(m.user_id, [])} for m in memberships]

    # ✅ Notes: DO NOT select_related('item') – it's a GenericFK
    notes_q = CampaignNote.objects.filter(campaign=campaign)
    if is_gm:
        notes = notes_q.select_related("author")
    else:
        notes = notes_q.filter(visibility="party").select_related("author")
    notes = notes.order_by("-created_at")

    # ✅ Inventory: same rule; only follow real FKs
    inventory = (PartyItem.objects
                 .filter(campaign=campaign)
                 .select_related("added_by"))

    inbox = (CampaignMessage.objects
             .filter(campaign=campaign)
             .filter(Q(sender=request.user) | Q(recipient=request.user))
             .select_related("sender", "recipient")
             .order_by("-created_at")[:50])

    note_form = CampaignNoteForm(user=request.user, campaign=campaign, is_gm=is_gm)
    message_form = MessageForm(campaign=campaign, user=request.user)

    context = {
        "campaign": campaign,
        "memberships": memberships,
        "memberships_with_chars": memberships_with_chars,
        "is_member": is_member,
        "is_gm": is_gm,
        "attached_characters": attached_characters,
        "attach_form": attach_form,
        "stats": stats,
        "notes": notes,
        "inventory": inventory,
        "inbox": inbox,
        "note_form": note_form,
        "message_form": message_form,
    }
    add_item_form = PartyItemForm()
    context.update({"add_item_form": add_item_form})
    return render(request, "campaigns/campaign_detail.html", context)
# campaigns/views.py

@login_required
def add_party_item(request, campaign_id):
    if request.method != "POST":
        raise Http404()
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("Only GMs can add party items.")

    form = PartyItemForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Pick an item and quantity.")
        return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#inventory")

    item = form.cleaned_data["item"]
    qty  = form.cleaned_data["quantity"]
    PartyItem.objects.create(campaign=campaign, item=item, quantity=qty, added_by=request.user)
    messages.success(request, f"Added {item.name} ×{qty} to the party.")
    return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#inventory")

# campaigns/views.py
@login_required
def join_campaign(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if CampaignMembership.objects.filter(campaign=campaign, user=request.user).exists():
        return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

    if request.method == "POST":
        form = JoinCampaignForm(request.POST, user=request.user, campaign=campaign)
        if form.is_valid():
            if campaign.join_password and form.cleaned_data.get("password") != campaign.join_password:
                messages.error(request, "Incorrect password.")
                return redirect("campaigns:join_campaign", campaign_id=campaign.id)

            CampaignMembership.objects.get_or_create(
                user=request.user, campaign=campaign, defaults={"role": "pc"}
            )
            ch = form.cleaned_data.get("character")
            if ch:
                ch.campaign = campaign
                ch.save()

            messages.success(request, "Joined the campaign.")
            return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

    else:
        form = JoinCampaignForm(user=request.user, campaign=campaign)

    return render(request, "campaigns/join_campaign.html", {"campaign": campaign, "form": form})


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

    form = AttachCharacterForm(request.POST, user=request.user)

    if not form.is_valid():
        messages.error(request, "Please pick a character.")
        return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

    character: Character = form.cleaned_data["character"]

    # Only attach your own characters (even GMs).
    if character.user_id != request.user.id:
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
def add_campaign_note(request, campaign_id):
    if request.method != "POST":
        raise Http404()
    campaign = get_object_or_404(Campaign, id=campaign_id)
    is_gm = _is_gm(request.user, campaign)
    form = CampaignNoteForm(request.POST, user=request.user, campaign=campaign, is_gm=is_gm)
    if not form.is_valid():
        messages.error(request, "Please fill in the note.")
        return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

    visibility = form.cleaned_data["visibility"]
    content    = form.cleaned_data["content"]

    note = CampaignNote.objects.create(
        campaign=campaign,
        author=request.user,
        visibility=visibility if is_gm else "party",
        content=content,
    )

    if is_gm and "equipment" in form.fields:
        item = form.cleaned_data.get("equipment")
        qty  = form.cleaned_data.get("quantity") or 0
        if item and qty > 0:
            PartyItem.objects.create(campaign=campaign, item=item, quantity=qty, added_by=request.user)
            note.item = item
            note.quantity = qty
            note.save(update_fields=["item","quantity"])
            messages.success(request, f"Note posted and {item.name} ×{qty} granted to the party.")
        else:
            messages.success(request, "Note posted.")
    else:
        messages.success(request, "Note posted.")

    return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#notes")


@login_required
def send_campaign_message(request, campaign_id):
    if request.method != "POST":
        raise Http404()
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if not campaign.members.filter(id=request.user.id).exists():
        return HttpResponseForbidden("Join the campaign first.")

    form = MessageForm(request.POST, campaign=campaign, user=request.user)
    if not form.is_valid():
        messages.error(request, "Please select a recipient and enter a message.")
        return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#messages")

    msg = CampaignMessage.objects.create(
        campaign=campaign,
        sender=request.user,
        recipient=form.cleaned_data["recipient"],
        content=form.cleaned_data["content"],
    )
    messages.success(request, "Message sent.")
    return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#messages")


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
