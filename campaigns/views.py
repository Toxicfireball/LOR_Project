# campaigns/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, Http404
from django.contrib import messages
from characters.models import Character, ClassFeat, CharacterFeat
from django.urls import reverse
from campaigns.models import CampaignMembership
from .models import EncounterEnemy

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

from .models import Campaign, CampaignMembership, EnemyTag
from .forms import (
    CampaignCreationForm, AttachCharacterForm, AssignSkillFeatsForm,
    EnemyTypeCreateForm, EnemyAbilityInlineFormSet, AddParticipantForm, SetParticipantInitiativeForm, SetEncounterEnemyHPForm, RecordDamageForm, UpdateEnemyNoteForm
)
from characters.models import Character
# BEFORE imports
# from .models import Campaign, CampaignMembership
# from .forms import CampaignCreationForm, AttachCharacterForm
# AFTER imports
from .models import Campaign, CampaignMembership, CampaignNote, PartyItem, CampaignMessage
from .forms import (
    CampaignCreationForm, AttachCharacterForm, CampaignNoteForm, PartyItemForm, MessageForm, JoinCampaignForm,
    AssignSkillFeatsForm,RecordEnemyToPCDamageForm,
    EnemyTypeForm, EnemyAbilityForm, EncounterForm, AddEnemyToEncounterForm,
    SetEncounterEnemyHPForm, AdjustEncounterEnemyHPForm,
    QuickAddEnemyForm,   # NEW
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
from .models import (
    Campaign, CampaignMembership, CampaignNote, PartyItem, CampaignMessage,
    EnemyType, EnemyAbility, Encounter, EncounterEnemy   # NEW
)
from .forms import (
    CampaignCreationForm, AttachCharacterForm, CampaignNoteForm, PartyItemForm, MessageForm, JoinCampaignForm,
    AssignSkillFeatsForm,                      # you already had this
    EnemyTypeForm, EnemyAbilityForm, EncounterForm, AddEnemyToEncounterForm,  # NEW
    SetEncounterEnemyHPForm, AdjustEncounterEnemyHPForm                       # NEW
)
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

    inventory = (PartyItem.objects
                .filter(campaign=campaign)
                .select_related("added_by", "claimed_by"))

    inbox = (CampaignMessage.objects
             .filter(campaign=campaign)
             .filter(Q(sender=request.user) | Q(recipient=request.user))
             .select_related("sender", "recipient")
             .order_by("-created_at")[:50])

    note_form = CampaignNoteForm(user=request.user, campaign=campaign, is_gm=is_gm)
    message_form = MessageForm(campaign=campaign, user=request.user)

    # … earlier context building …
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

    if is_gm:
        context["pending_bgs"] = list(
            campaign.pending_backgrounds.filter(status="pending").order_by("-created_at")
        )
    assign_skill_feats_form = AssignSkillFeatsForm(campaign=campaign)
    context["assign_skill_feats_form"] = assign_skill_feats_form
    add_item_form = PartyItemForm()
    context["add_item_form"] = add_item_form
    encounters = list(campaign.encounters.all().only("id","name","description","created_at"))
    context["encounters"] = encounters
    context["enemy_types"] = (EnemyType.objects
        .filter(Q(campaign__isnull=True) | Q(campaign=campaign))
        .prefetch_related("tags")
        .order_by("name")
    )
    context["encounter_form"] = EncounterForm()
    context["quick_add_enemy_form"] = QuickAddEnemyForm(campaign=campaign)  # NEW


    return render(request, "campaigns/campaign_detail.html", context)

@login_required
def quick_add_enemy(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST":
        raise Http404()

    form = QuickAddEnemyForm(request.POST, campaign=campaign)
    if not form.is_valid():
        messages.error(request, "Pick encounter, enemy, and count.")
        return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#encounters")

    enc = form.cleaned_data["encounter"]
    et  = form.cleaned_data["enemy_type"]
    side = form.cleaned_data["side"]
    cnt = form.cleaned_data["count"]
    for _ in range(cnt):
        EncounterEnemy.objects.create(encounter=enc, enemy_type=et, side=side, max_hp=et.hp, current_hp=et.hp)

    messages.success(request, f"Added {cnt} × {et.name} to '{enc.name}'.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)


# campaigns/views.py
from django.shortcuts import get_object_or_404
from django.utils import timezone
from characters.models import PendingBackground, Background

@login_required
def approve_pending_bg(request, campaign_id, pb_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    pb = get_object_or_404(PendingBackground, pk=pb_id, campaign=campaign)
    if request.method != "POST": raise Http404()

    # Create/overwrite approved Background with same code
    bg, _ = Background.objects.update_or_create(
        code=pb.code,
        defaults=dict(
            name=pb.name,
            description=pb.description,
            primary_ability=pb.primary_ability, primary_bonus=pb.primary_bonus,
            secondary_ability=pb.secondary_ability, secondary_bonus=pb.secondary_bonus,
            primary_selection_mode=pb.primary_selection_mode,
            secondary_selection_mode=pb.secondary_selection_mode,
            primary_skill_type=pb.primary_skill_type, primary_skill_id=pb.primary_skill_id,
            secondary_skill_type=pb.secondary_skill_type, secondary_skill_id=pb.secondary_skill_id,
        )
    )
    pb.status = "approved"
    pb.decided_at = timezone.now()
    pb.save(update_fields=["status","decided_at"])
    messages.success(request, f"Approved background '{bg.name}'.")
    return redirect("campaigns:campaign_detail", campaign_id=campaign.id)
@login_required
def assign_skill_feats(request, campaign_id):
    if request.method != "POST":
        raise Http404()
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")

    form = AssignSkillFeatsForm(request.POST, campaign=campaign)
    if not form.is_valid():
        messages.error(request, "; ".join([str(e) for e in form.errors.get("__all__", [])]) or "Fix the errors below.")
        return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#skillfeats")

    feats = [f for f in [form.cleaned_data["feat1"], form.cleaned_data.get("feat2")] if f]
    targets = (list(campaign.characters.all())
               if form.cleaned_data.get("apply_to_all")
               else [form.cleaned_data["character"]])

    created = skipped = 0
    for ch in targets:
        for feat in feats:
            if CharacterFeat.objects.filter(character=ch, feat=feat).exists():
                skipped += 1
                continue
            CharacterFeat.objects.create(character=ch, feat=feat, level=ch.level or 0)
            created += 1

    if created:
        messages.success(request, f"Granted {created} Skill Feat(s). Skipped {skipped} already owned.")
    else:
        messages.info(request, "No feats granted (likely duplicates).")

    return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#skillfeats")

@login_required
def reject_pending_bg(request, campaign_id, pb_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    pb = get_object_or_404(PendingBackground, pk=pb_id, campaign=campaign)
    if request.method != "POST": raise Http404()
    note = request.POST.get("gm_note","").strip()
    pb.status = "rejected"
    pb.gm_note = note
    pb.decided_at = timezone.now()
    pb.save(update_fields=["status","gm_note","decided_at"])
    messages.info(request, f"Rejected background '{pb.name}'.")
    return redirect("campaigns:campaign_detail", campaign_id=campaign.id)

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
# ====== ENEMIES & ENCOUNTERS (GM only) =======================================

@login_required
def create_enemy_type(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST": raise Http404()
    form = EnemyTypeForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Fix the enemy fields.")
        return redirect("campaigns:campaign_detail", campaign_id=campaign.id)
    et = form.save()
    messages.success(request, f"Enemy '{et.name}' created.")
    return redirect("campaigns:campaign_detail", campaign_id=campaign.id)


@login_required
def add_enemy_ability(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST": raise Http404()
    form = EnemyAbilityForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Fill in ability details.")
        return redirect("campaigns:campaign_detail", campaign_id=campaign.id)
    ab = form.save()
    messages.success(request, f"Added {ab.get_ability_type_display()} ability to {ab.enemy_type.name}.")
    return redirect("campaigns:campaign_detail", campaign_id=campaign.id)


@login_required
def create_encounter(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST": raise Http404()
    form = EncounterForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Name your encounter.")
        return redirect("campaigns:campaign_detail", campaign_id=campaign.id)
    enc = form.save(commit=False)
    enc.campaign = campaign
    enc.save()
    messages.success(request, f"Encounter '{enc.name}' created.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

from .forms import AddParticipantForm, SetParticipantInitiativeForm, RecordDamageForm, UpdateEnemyNoteForm
from .models import EncounterParticipant, DamageEvent, EncounterEnemy

@login_required
def add_participant(request, campaign_id, encounter_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    enc = get_object_or_404(Encounter, id=encounter_id, campaign=campaign)
    if not _is_gm(request.user, campaign):  # adjust policy if players can add self
        return HttpResponseForbidden("GM only.")
    if request.method != "POST": raise Http404()

    form = AddParticipantForm(request.POST, campaign=campaign)
    if not form.is_valid():
        messages.error(request, "Pick a character.")
        return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

    p, created = EncounterParticipant.objects.get_or_create(
        encounter=enc,
        character=form.cleaned_data["character"],
        defaults={
            "role": form.cleaned_data["role"],
            "initiative": form.cleaned_data.get("initiative"),
            "added_by": request.user,
        },
    )
    if created:
        messages.success(request, f"Added {p.character.name} to initiative.")
    else:
        messages.info(request, f"{p.character.name} is already in this encounter.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)


@login_required
def set_participant_initiative(request, campaign_id, encounter_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    enc = get_object_or_404(Encounter, id=encounter_id, campaign=campaign)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST": raise Http404()

    form = SetParticipantInitiativeForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a valid initiative.")
        return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

    p = get_object_or_404(EncounterParticipant, id=form.cleaned_data["participant_id"], encounter=enc)
    p.initiative = form.cleaned_data["initiative"]
    p.save(update_fields=["initiative"])
    messages.success(request, f"{p.character.name} initiative set to {p.initiative}.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)


@login_required
def remove_participant(request, campaign_id, encounter_id, participant_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    enc = get_object_or_404(Encounter, id=encounter_id, campaign=campaign)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST": raise Http404()

    p = get_object_or_404(EncounterParticipant, id=participant_id, encounter=enc)
    name = p.character.name
    p.delete()
    messages.info(request, f"Removed {name} from encounter.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)


def record_damage(request, campaign_id, encounter_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    enc = get_object_or_404(Encounter, id=encounter_id, campaign=campaign)
    if request.method != "POST": raise Http404()

    mode = request.POST.get("mode", "pc_to_enemy")

    if mode == "enemy_to_pc":
        form = RecordEnemyToPCDamageForm(request.POST, campaign=campaign)
        if not form.is_valid():
            messages.error(request, "Enter a valid enemy → player damage entry.")
            return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

        attacker_ee = get_object_or_404(EncounterEnemy, id=form.cleaned_data["attacker_ee_id"], encounter=enc)
        victim = form.cleaned_data["target_character"]
        amount = form.cleaned_data["amount"]
        note = form.cleaned_data.get("note", "")

        # Apply damage to PLAYERS? (We don't track PC HP here, so just log the event)
        DamageEvent.objects.create(
            encounter=enc,
            attacker_enemy=attacker_ee,
            target_character=victim,
            kind="dmg",
            amount=amount,
            note=note,
        )
        messages.success(request, f"{attacker_ee.display_name} hit {victim.name} for {amount}.")
        return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

    # default: PC → Enemy (existing flow)
    form = RecordDamageForm(request.POST, campaign=campaign)
    if not form.is_valid():
        messages.error(request, "Enter a valid damage/heal entry.")
        return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

    ee = get_object_or_404(EncounterEnemy, id=form.cleaned_data["ee_id"], encounter=enc)
    amount = form.cleaned_data["amount"]
    kind = form.cleaned_data["kind"]
    attacker = form.cleaned_data.get("attacker")

    # Apply HP to ENEMY
    signed = -amount if kind == "dmg" else amount
    ee.current_hp = max(min(ee.current_hp + signed, ee.max_hp), -999)
    ee.save(update_fields=["current_hp"])

    DamageEvent.objects.create(
        encounter=enc,
        attacker_user=request.user,
        attacker_character=attacker,
        target_enemy=ee,             # <- changed from enemy=ee
        kind=kind,
        amount=amount,
        note=form.cleaned_data.get("note", ""),
    )

    verb = "damaged" if kind == "dmg" else "healed"
    who = attacker.name if attacker else request.user.username
    messages.success(request, f"{who} {verb} {ee.display_name} for {amount}. Now {ee.current_hp}/{ee.max_hp}.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

from django.db.models import Sum, Max, Count
@login_required
def campaign_damage_stats(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not campaign.members.filter(id=request.user.id).exists():
        return HttpResponseForbidden("Join the campaign first.")

    # All damage events for this campaign
    base = DamageEvent.objects.filter(encounter__campaign=campaign, kind="dmg")

    # PC -> ENEMY (team damage dealt)
    outgoing = base.filter(target_enemy__isnull=False)
    team_total = outgoing.aggregate(total=Sum("amount"))["total"] or 0

    by_char = (outgoing.values("attacker_character__id", "attacker_character__name")
                      .annotate(total=Sum("amount"), hits=Count("id"))
                      .order_by("-total"))
    for r in by_char:
        r["share_pct"] = round((r["total"] / team_total) * 100, 1) if team_total else 0.0

    per_enc = (outgoing.values("attacker_character__id", "attacker_character__name")
                       .annotate(encounters=Count("encounter", distinct=True), total=Sum("amount"))
                       .order_by("-total"))
    for r in per_enc:
        r["avg_per_encounter"] = (r["total"] / r["encounters"]) if r["encounters"] else 0

    dmg_by_enemy_type = (outgoing.values("target_enemy__enemy_type__name", "target_enemy__side")
                                 .annotate(total=Sum("amount"), hits=Count("id"))
                                 .order_by("-total"))
    for r in dmg_by_enemy_type:
        r["share_pct"] = round((r["total"] / (team_total or 1)) * 100, 1)

    highest_out = (outgoing.order_by("-amount")
                          .select_related("attacker_character", "attacker_user",
                                          "target_enemy__enemy_type", "encounter")
                          .first())

    # ENEMY -> PC (damage taken)
    incoming = base.filter(target_character__isnull=False, attacker_enemy__isnull=False)
    taken_total = incoming.aggregate(total=Sum("amount"))["total"] or 0

    taken_by_pc = (incoming.values("target_character__id", "target_character__name")
                            .annotate(total=Sum("amount"), hits=Count("id"))
                            .order_by("-total"))
    for r in taken_by_pc:
        r["share_pct"] = round((r["total"] / taken_total) * 100, 1) if taken_total else 0.0

    src_enemy_type = (incoming.values("attacker_enemy__enemy_type__name", "attacker_enemy__side")
                               .annotate(total=Sum("amount"), hits=Count("id"))
                               .order_by("-total"))
    for r in src_enemy_type:
        r["share_pct"] = round((r["total"] / (taken_total or 1)) * 100, 1)

    highest_in = (incoming.order_by("-amount")
                          .select_related("attacker_enemy__enemy_type",
                                          "target_character", "encounter")
                          .first())

    context = {
        "campaign": campaign,
        # dealt
        "by_char": list(by_char),
        "per_enc": list(per_enc),
        "team_total": team_total,
        "dmg_by_enemy_type": list(dmg_by_enemy_type),
        "highest_out": highest_out,
        # taken
        "taken_by_pc": list(taken_by_pc),
        "taken_total": taken_total,
        "src_enemy_type": list(src_enemy_type),
        "highest_in": highest_in,
    }
    return render(request, "campaigns/campaign_damage_stats.html", context)



@login_required
def update_enemy_note(request, campaign_id, encounter_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    enc = get_object_or_404(Encounter, id=encounter_id, campaign=campaign)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST": raise Http404()

    form = UpdateEnemyNoteForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a valid note.")
        return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

    ee = get_object_or_404(EncounterEnemy, id=form.cleaned_data["ee_id"], encounter=enc)
    ee.notes = form.cleaned_data["notes"] or ""
    ee.save(update_fields=["notes"])
    messages.success(request, f"Updated notes for {ee.display_name}.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)
from .models import EncounterParticipant, EncounterEnemy

@login_required
def set_combat_initiative(request, campaign_id, encounter_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    enc = get_object_or_404(Encounter, id=encounter_id, campaign=campaign)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST": raise Http404()

    kind = request.POST.get("kind")
    obj_id = request.POST.get("id")
    try:
        init = int(request.POST.get("initiative"))
    except (TypeError, ValueError):
        messages.error(request, "Enter a valid initiative.")
        return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

    if kind == "enemy":
        ee = get_object_or_404(EncounterEnemy, id=obj_id, encounter=enc)
        ee.initiative = init
        ee.save(update_fields=["initiative"])
        messages.success(request, f"{ee.display_name} initiative set to {init}.")
    elif kind == "pc":
        p = get_object_or_404(EncounterParticipant, id=obj_id, encounter=enc)
        p.initiative = init
        p.save(update_fields=["initiative"])
        messages.success(request, f"{p.character.name} initiative set to {init}.")
    else:
        messages.error(request, "Unknown combatant.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)


@login_required
def nudge_combat_initiative(request, campaign_id, encounter_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    enc = get_object_or_404(Encounter, id=encounter_id, campaign=campaign)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST": raise Http404()

    kind = request.POST.get("kind")
    obj_id = request.POST.get("id")
    delta = int(request.POST.get("delta", "0"))

    if kind == "enemy":
        ee = get_object_or_404(EncounterEnemy, id=obj_id, encounter=enc)
        ee.initiative = (ee.initiative or 0) + delta
        ee.save(update_fields=["initiative"])
    elif kind == "pc":
        p = get_object_or_404(EncounterParticipant, id=obj_id, encounter=enc)
        p.initiative = (p.initiative or 0) + delta
        p.save(update_fields=["initiative"])
    else:
        messages.error(request, "Unknown combatant.")
        return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

    sign = "+" if delta >= 0 else ""
    messages.success(request, f"Initiative {sign}{delta}.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

@login_required
def encounter_detail(request, campaign_id, encounter_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    enc = get_object_or_404(Encounter, id=encounter_id, campaign=campaign)

    is_member = campaign.members.filter(id=request.user.id).exists()
    is_gm = _is_gm(request.user, campaign)

    enemies = (
        enc.enemies
        .select_related("enemy_type")
        .prefetch_related("enemy_type__abilities", "enemy_type__tags")
        .order_by("id")
    )

    add_form = AddEnemyToEncounterForm()
    add_form.fields["enemy_type"].queryset = EnemyType.objects.filter(
        Q(campaign__isnull=True) | Q(campaign=campaign)
    ).order_by("name")

    set_hp_form = SetEncounterEnemyHPForm()
    adj_hp_form = AdjustEncounterEnemyHPForm()

    # NEW: bring in participants (players) and make a single Combat list (enemies + PCs)
    participants = enc.participants.select_related("character", "character__user")

    # Build a simple, sortable structure
    combat = []
    for ee in enemies:
        combat.append({
            "kind": "enemy",
            "id": ee.id,
            "name": ee.display_name,
            "sub": ee.enemy_type.name,
            "initiative": ee.initiative if ee.initiative is not None else ee.enemy_type.initiative,
            "hp": (ee.current_hp, ee.max_hp),
            "obj": ee,
        })
    for p in participants:
        combat.append({
            "kind": "pc",
            "id": p.id,
            "name": f"{p.character.user.username} · {p.character.name}",
            "sub": "Player",
            "initiative": p.initiative,
            "hp": None,  # PCs aren't tracked here
            "obj": p,
        })
    # Highest initiative first; None sorts last
    combat.sort(key=lambda r: (999999 if r["initiative"] is None else -r["initiative"], r["name"]))



    add_participant_form = AddParticipantForm(campaign=campaign, encounter=enc)  # NEW
    colspan = 6 if is_gm else 4
    return render(request, "campaigns/encounter_detail.html", {
        "campaign": campaign,
        "encounter": enc,
        "enemies": enemies,
        "is_member": is_member,
        "is_gm": is_gm,
        "add_form": add_form,
        "set_hp_form": set_hp_form,
        "adj_hp_form": adj_hp_form,
        "participants": participants,
        "combat": combat,
        "combat_colspan": colspan,
        "add_participant_form": add_participant_form,

    })

@login_required
def delete_enemy_type(request, campaign_id, et_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST":
        raise Http404()

    et = get_object_or_404(
        EnemyType,
        id=et_id,
        # allow deleting either global or this campaign's types; restrict global deletion to GMs here
        # who are in this campaign (adjust policy if you want stricter)
    )

    # block deletion if used by any EncounterEnemy
    in_use = EncounterEnemy.objects.filter(enemy_type=et).exists()
    if in_use:
        messages.error(request, f"Cannot delete '{et.name}' – it is used in one or more encounters.")
        return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#encounters")

    et.delete()
    messages.success(request, f"Enemy Type '{et.name}' deleted.")
    return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#encounters")

# campaigns/views.py

from django.utils import timezone
from .models import PartyItem

@login_required
def claim_party_item(request, campaign_id, pi_id):
    if request.method != "POST":
        raise Http404()
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if not campaign.members.filter(id=request.user.id).exists():
        return HttpResponseForbidden("Join the campaign first.")

    # You can choose: allow any member to claim, or only the character they have attached.
    # Below assumes a player may claim for one of their attached characters in this campaign.
    char = (campaign.characters
            .filter(user=request.user)
            .order_by("id")
            .first())
    if not char:
        messages.error(request, "Attach a character to claim party items.")
        return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#inventory")

    it = get_object_or_404(PartyItem, id=pi_id, campaign=campaign)

    if it.is_claimed:
        messages.info(request, f"Already claimed by {it.claimed_by.name}.")
        return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#inventory")

    it.claimed_by = char
    it.claimed_at = timezone.now()
    it.save(update_fields=["claimed_by", "claimed_at"])
    messages.success(request, f"You claimed {it.item.name} ×{it.quantity} for {char.name}.")
    return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#inventory")


@login_required
def unclaim_party_item(request, campaign_id, pi_id):
    if request.method != "POST":
        raise Http404()
    campaign = get_object_or_404(Campaign, id=campaign_id)
    it = get_object_or_404(PartyItem, id=pi_id, campaign=campaign)

    # Policy: GM can unclaim anyone; a player can only unclaim if they claimed it.
    is_gm = _is_gm(request.user, campaign)
    if not is_gm and (not it.claimed_by or it.claimed_by.user_id != request.user.id):
        return HttpResponseForbidden("You can only unclaim items you claimed.")

    if not it.is_claimed:
        messages.info(request, "That item is not claimed.")
    else:
        it.claimed_by = None
        it.claimed_at = None
        it.save(update_fields=["claimed_by", "claimed_at"])
        messages.success(request, "Item returned to party inventory.")
    return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#inventory")


@login_required
def remove_party_item(request, campaign_id, pi_id):
    """Delete inventory rows — but block if the item is claimed."""
    if request.method != "POST":
        raise Http404()
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("Only GMs can remove party items.")
    it = get_object_or_404(PartyItem, id=pi_id, campaign=campaign)

    if it.is_claimed:
        messages.error(
            request,
            f"Cannot remove {it.item.name} — it’s currently claimed by {it.claimed_by.name}. Unclaim it first."
        )
        return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#inventory")

    name = it.item.name
    it.delete()
    messages.info(request, f"Removed {name} from party inventory.")
    return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#inventory")

@login_required
def new_enemy_type(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")

    if request.method == "POST":
        form = EnemyTypeCreateForm(request.POST, campaign=campaign)
        if form.is_valid():
            et = form.save(commit=False)
            et.save()
            form.save_m2m()
            formset = EnemyAbilityInlineFormSet(request.POST, instance=et, prefix="ab")
            if formset.is_valid():
                formset.save()
                messages.success(
                    request,
                    f"Enemy Type '{et.name}' created ({'Global' if et.campaign_id is None else campaign.name})."
                )
                return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#encounters")
        else:
            formset = EnemyAbilityInlineFormSet(request.POST, prefix="ab")
    else:
        form = EnemyTypeCreateForm(campaign=campaign)
        # empty formset for inline abilities
        dummy = EnemyType(campaign=campaign, name="__draft__")
        formset = EnemyAbilityInlineFormSet(instance=dummy, prefix="ab")

    tags = EnemyTag.objects.all()
    return render(request, "campaigns/enemytype_form.html", {
        "campaign": campaign,
        "form": form,
        "formset": formset,
        "tags": tags,
    })

@login_required
def add_enemy_to_encounter(request, campaign_id, encounter_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    enc = get_object_or_404(Encounter, id=encounter_id, campaign=campaign)
    if request.method != "POST": raise Http404()

    form = AddEnemyToEncounterForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Pick an enemy and count.")
        return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)

    et = form.cleaned_data["enemy_type"]
    side = form.cleaned_data["side"]
    count = form.cleaned_data["count"]
    created = 0
    for _ in range(count):
        EncounterEnemy.objects.create(
            encounter=enc,
            enemy_type=et,
            side=side,
            max_hp=et.hp,
            current_hp=et.hp,
        )
        created += 1


    messages.success(request, f"Added {created} × {et.name}.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)


@login_required
def set_encounter_enemy_hp(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST": raise Http404()

    form = SetEncounterEnemyHPForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a valid HP value.")
        # Try to bounce to referring page
        return redirect(request.META.get("HTTP_REFERER", "campaigns:campaign_detail"), campaign_id=campaign.id)

    ee = get_object_or_404(EncounterEnemy, id=form.cleaned_data["ee_id"], encounter__campaign=campaign)
    ee.current_hp = form.cleaned_data["current_hp"]
    # keep within [<= max], but allow negatives if you like. Here clamp min at -999 for safety.
    ee.current_hp = max(min(ee.current_hp, ee.max_hp), -999)
    ee.save(update_fields=["current_hp"])

    messages.success(request, f"{ee.display_name} HP set to {ee.current_hp}/{ee.max_hp}.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=ee.encounter_id)

@login_required
def edit_enemy_type(request, campaign_id, et_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    et = get_object_or_404(EnemyType, id=et_id)

    if request.method == "POST":
        form = EnemyTypeCreateForm(request.POST, instance=et, campaign=campaign)
        formset = EnemyAbilityInlineFormSet(request.POST, instance=et, prefix="ab")
        if form.is_valid() and formset.is_valid():
            et = form.save()
            form.save_m2m()
            formset.save()
            messages.success(request, f"Enemy Type '{et.name}' updated.")
            return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#encounters")
        # 👇 if invalid, show a clear error and fall through to render the bound forms
        messages.error(request, "Please fix the errors below and try again.")
    else:
        form = EnemyTypeCreateForm(instance=et, campaign=campaign)
        formset = EnemyAbilityInlineFormSet(instance=et, prefix="ab")

    return render(request, "campaigns/enemytype_form.html", {
        "campaign": campaign,
        "form": form,
        "formset": formset,
        "tags": EnemyTag.objects.all(),
    })
    
    
@login_required
def delete_encounter(request, campaign_id, encounter_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST":
        raise Http404()

    enc = get_object_or_404(Encounter, id=encounter_id, campaign=campaign)
    name = enc.name
    enc.delete()  # relies on your FK cascade to remove EncounterEnemy rows
    messages.info(request, f"Encounter '{name}' deleted.")
    return redirect(f"{reverse('campaigns:campaign_detail', args=[campaign.id])}#encounters")

@login_required
def adjust_encounter_enemy_hp(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    if request.method != "POST": raise Http404()

    form = AdjustEncounterEnemyHPForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid adjustment.")
        return redirect(request.META.get("HTTP_REFERER", "campaigns:campaign_detail"), campaign_id=campaign.id)

    ee = get_object_or_404(EncounterEnemy, id=form.cleaned_data["ee_id"], encounter__campaign=campaign)
    ee.current_hp = ee.current_hp + form.cleaned_data["delta"]
    ee.current_hp = max(min(ee.current_hp, ee.max_hp), -999)
    ee.save(update_fields=["current_hp"])

    sign = "+" if form.cleaned_data["delta"] >= 0 else ""
    messages.success(request, f"{ee.display_name} HP {sign}{form.cleaned_data['delta']} → {ee.current_hp}/{ee.max_hp}.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=ee.encounter_id)


@login_required
def remove_encounter_enemy(request, campaign_id, encounter_id, ee_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM only.")
    enc = get_object_or_404(Encounter, id=encounter_id, campaign=campaign)
    if request.method != "POST": raise Http404()

    ee = get_object_or_404(EncounterEnemy, id=ee_id, encounter=enc)
    name = ee.display_name
    ee.delete()
    messages.info(request, f"Removed {name}.")
    return redirect("campaigns:encounter_detail", campaign_id=campaign.id, encounter_id=enc.id)
