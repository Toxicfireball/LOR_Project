from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.forms import modelform_factory

from .forms import RegistrationForm
from .models import EmailVerification, UserEmail
from .utils import send_verification_email
from .utils import send_verification_email, EmailSendError

def register(request):
    """
    New users:
      - Save user
      - Create EmailVerification(purpose=signup)
      - Send email with /accounts/verify/<token>/
      - Show 'check your email' page (do NOT login yet)
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserEmail.objects.get_or_create(user=user)

            ev = EmailVerification.objects.create(
                user=user,
                email=user.email,
                purpose=EmailVerification.PURPOSE_SIGNUP
            )
            # register():
            verify_url = request.build_absolute_uri(
                reverse('accounts:verify_email', args=[str(ev.token)])
            )
            try:
                send_verification_email(user, user.email, verify_url=verify_url)
                return render(request, 'accounts/check_email.html', {
                    'email': user.email, 'verify_url': verify_url,
                })
            except EmailSendError as e:
                return render(request, 'accounts/check_email.html', {
                    'email': user.email, 'verify_url': verify_url, 'error': str(e),
                })

    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def request_verification(request):
    meta = getattr(request.user, "email_meta", None)
    if meta and meta.is_verified:
        messages.info(request, "Your email is already verified.")
        return redirect('campaigns:campaign_list')

    if request.method == "POST":
        ev = EmailVerification.objects.create(
            user=request.user,
            email=request.user.email,
            purpose=EmailVerification.PURPOSE_SIGNUP
        )
        verify_url = request.build_absolute_uri(
            reverse('accounts:verify_email', args=[str(ev.token)])
        )
        try:
            send_verification_email(request.user, request.user.email, verify_url=verify_url)
            return render(request, 'accounts/check_email.html', {
                'email': request.user.email, 'verify_url': verify_url,
            })
        except EmailSendError as e:
            return render(request, 'accounts/check_email.html', {
                'email': request.user.email, 'verify_url': verify_url, 'error': str(e),
            })


    return render(request, 'accounts/request_verification.html', {})
# campaigns/views.py
from math import floor
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.contrib.contenttypes.models import ContentType

from campaigns.models import Campaign
from characters.models import (
    Character,
    Skill,
    CharacterSkillProficiency,
    CharacterSkillRating,
    ProficiencyLevel,
    CharacterClassProgress,
    ClassProficiencyProgress,
    ProficiencyTier,
    CharacterFeature,
    SpecialItem,
    SpecialItemTraitValue,
)

# --- Helpers --------------------------------------------------------------

def _is_gm(user, campaign: Campaign) -> bool:
    """
    Adjust this to your real membership model/roles.
    Assumes Campaign has 'memberships' with a 'role' (owner/gm/player).
    """
    return campaign.memberships.filter(user=user, role__in=["owner", "gm"]).exists()

def _ability_mod(score: int | None) -> int:
    score = int(score or 10)
    return floor((score - 10) / 2)

def _skill_total(character: Character, skill_name: str) -> int:
    """
    ability mod (from Skill.ability) + skill proficiency bonus + extra bonus_points.
    """
    try:
        sk = Skill.objects.get(name__iexact=skill_name.strip())
    except Skill.DoesNotExist:
        return 0

    # base from the governing ability
    total = _ability_mod(getattr(character, sk.ability, 10))

    # proficiency from CharacterSkillProficiency
    skill_ct = ContentType.objects.get_for_model(Skill)
    prof = (CharacterSkillProficiency.objects
            .filter(character=character,
                    selected_skill_type=skill_ct,
                    selected_skill_id=sk.id)
            .select_related("proficiency")
            .first())
    if prof and isinstance(prof.proficiency, ProficiencyLevel):
        try:
            total += int(prof.proficiency.bonus or 0)
        except (TypeError, ValueError):
            pass

    # extra per-skill points (optional)
    rating = CharacterSkillRating.objects.filter(character=character, skill=sk).first()
    if rating:
        try:
            total += int(rating.bonus_points or 0)
        except (TypeError, ValueError):
            pass

    return int(total)

def _class_progress_prof_bonus(character: Character, code: str) -> int:
    """
    Highest ProficiencyTier.bonus reached for a given proficiency 'code'
    across all of the character's classes at their current class levels.
    Ignores weapon/armor groups for simplicity.
    """
    best = 0
    # the character's spreads across base classes
    for cp in CharacterClassProgress.objects.filter(character=character).select_related("character_class"):
        if not cp.levels:
            continue
        rows = (ClassProficiencyProgress.objects
                .filter(character_class=cp.character_class,
                        proficiency_type=code,
                        armor_group__isnull=True,
                        weapon_group__isnull=True,
                        at_level__lte=cp.levels)
                .select_related("tier"))
        for r in rows:
            if isinstance(r.tier, ProficiencyTier):
                try:
                    best = max(best, int(r.tier.bonus or 0))
                except (TypeError, ValueError):
                    pass
    return int(best)

def _feature_or_item_prof_override(character: Character, code: str) -> int:
    """
    Highest override coming from:
      - ClassFeature(kind='modify_proficiency', target=code, amount=tier)
      - Active SpecialItem trait values that set modify_proficiency on code
    """
    best = 0
    # features
    feats = (CharacterFeature.objects
             .filter(character=character,
                     feature__kind="modify_proficiency",
                     feature__modify_proficiency_target=code,
                     feature__modify_proficiency_amount__isnull=False)
             .select_related("feature__modify_proficiency_amount"))
    for cf in feats:
        tier = getattr(cf.feature, "modify_proficiency_amount", None)
        if isinstance(tier, ProficiencyTier):
            try:
                best = max(best, int(tier.bonus or 0))
            except (TypeError, ValueError):
                pass

    # items (active via CharacterActivation)
    try:
        si_ct = ContentType.objects.get_for_model(SpecialItem)
        active_ids = list(character.activations
                          .filter(content_type=si_ct, is_active=True)
                          .values_list("object_id", flat=True))
        if active_ids:
            for tv in SpecialItemTraitValue.objects.filter(
                special_item_id__in=active_ids,
                modify_proficiency_target=code
            ):
                try:
                    best = max(best, int(tv.modify_proficiency_amount))
                except (TypeError, ValueError):
                    pass
    except Exception:
        # if activations or items aren't used yet, just ignore
        pass

    return int(best)

def _prof_bonus(character: Character, code: str) -> int:
    return max(_class_progress_prof_bonus(character, code),
               _feature_or_item_prof_override(character, code))

def _equipped_armor_value(character: Character) -> int:
    """
    Simple heuristic: find the active SpecialItem with an attached Armor, take highest armor_value.
    If you have a dedicated 'equipped' relation, switch to that.
    """
    try:
        si_ct = ContentType.objects.get_for_model(SpecialItem)
        best = 0
        for act in character.activations.filter(content_type=si_ct, is_active=True):
            si: SpecialItem = act.target
            if getattr(si, "armor", None) and getattr(si.armor, "armor_value", None) is not None:
                best = max(best, int(si.armor.armor_value))
        return best
    except Exception:
        return 0

# --- The page --------------------------------------------------------------

@login_required
def gm_dashboard(request, campaign_id: int):
    campaign = get_object_or_404(Campaign, pk=campaign_id)

    if not _is_gm(request.user, campaign):
        return HttpResponseForbidden("GM access only.")

    chars = (Character.objects
             .filter(campaign=campaign, status="active")
             .select_related("user", "race", "subrace"))

    rows = []
    for c in chars:
        dex_mod = _ability_mod(c.dexterity)
        con_mod = _ability_mod(c.constitution)
        wis_mod = _ability_mod(c.wisdom)

        passive_perception = 10 + _skill_total(c, "Perception")
        dodge = 10 + dex_mod + _prof_bonus(c, "dodge")
        armor = _equipped_armor_value(c)
        reflex = dex_mod + _prof_bonus(c, "reflex")
        fortitude = con_mod + _prof_bonus(c, "fortitude")
        will = wis_mod + _prof_bonus(c, "will")

        rows.append({
            "id": c.id,
            "name": c.name,
            "player": getattr(c.user, "username", "—"),
            "level": c.level,
            "speed": c.effective_speed if hasattr(c, "effective_speed") else 30,
            "hp": int(c.HP or 0),
            "temp": int(c.temp_HP or 0),
            "pp": int(passive_perception),
            "dodge": int(dodge),
            "armor": int(armor),
            "reflex": int(reflex),
            "fortitude": int(fortitude),
            "will": int(will),
            "race": str(c.race) if c.race_id else "—",
        })

    context = {
        "campaign": campaign,
        "rows": rows,
    }
    return render(request, "campaigns/gm_dashboard.html", context)

@login_required
def change_email(request):
    if request.method == "POST":
        new_email = (request.POST.get("new_email") or "").strip()
        if not new_email:
            messages.error(request, "Please enter a new email.")
            return redirect('accounts:change_email')

        ev = EmailVerification.objects.create(
            user=request.user,
            email=new_email,
            purpose=EmailVerification.PURPOSE_CHANGE
        )
        verify_url = request.build_absolute_uri(
            reverse('accounts:verify_email', args=[str(ev.token)])
        )
        try:
            send_verification_email(request.user, new_email, verify_url=verify_url)
            return render(request, 'accounts/check_email.html', {
                'email': new_email, 'verify_url': verify_url,
            })
        except EmailSendError as e:
            return render(request, 'accounts/check_email.html', {
                'email': new_email, 'verify_url': verify_url, 'error': str(e),
            })

    return render(request, 'accounts/change_email.html', {})

def verify_email(request, token):
    ev = get_object_or_404(EmailVerification, token=token, used_at__isnull=True)
    meta, _ = UserEmail.objects.get_or_create(user=ev.user)

    if ev.purpose == EmailVerification.PURPOSE_SIGNUP:
        meta.is_verified = True
        meta.save(update_fields=["is_verified"])
        ev.mark_used()
        login(request, ev.user)
        return render(request, 'accounts/verify_result.html', {
            'ok': True,
            'title': "Email verified",
            'message': "Your email has been verified. You are now signed in.",
        })

    elif ev.purpose == EmailVerification.PURPOSE_CHANGE:
        ev.user.email = ev.email
        ev.user.save(update_fields=["email"])
        meta.is_verified = True
        meta.save(update_fields=["is_verified"])
        ev.mark_used()
        return render(request, 'accounts/verify_result.html', {
            'ok': True,
            'title': "Email changed & verified",
            'message': f"Your email has been changed to {ev.email} and verified.",
        })

    return render(request, 'accounts/verify_result.html', {
        'ok': False,
        'title': "Invalid verification",
        'message': "This verification link is not valid.",
    })

@login_required
def submission_list(request):
    subs = request.user.submissions.order_by('-created_at')
    return render(request, 'accounts/submission_list.html', {'subs': subs})


