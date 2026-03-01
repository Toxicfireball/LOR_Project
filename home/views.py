from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch

# import your models
from characters.models import Character
from campaigns.models import Campaign, CampaignMembership
from collections import OrderedDict
from django.shortcuts import render
from django.db.models import Count

from characters.models import PatchNote

from characters.models import Character, ModelChangeLog
from campaigns.models import CampaignMembership
from collections import OrderedDict
from django.db.models import Count
from characters.models import PatchNote, PatchChange
def _get_latest_patch():
    """
    Returns None if no published patches exist.
    Otherwise returns:
      {
        "group_key": str,
        "label": str,
        "published_at": datetime,
        "counts": OrderedDict({category_name: n, ...})
      }
    """
    base = ModelChangeLog.objects.filter(is_published=True)

    latest = (
        base.exclude(publish_group__isnull=True)
            .exclude(publish_group__exact="")
            .order_by("-published_at", "-occurred_at")
            .first()
    )
    if not latest:
        return None

    group_key = latest.publish_group.strip()
    published_at = latest.published_at or latest.occurred_at

    # count entries per category inside this patch
    rows = (
        base.filter(publish_group=group_key)
            .values("category__name")
            .annotate(n=Count("id"))
            .order_by("category__sort_order", "category__name")
    )

    counts = OrderedDict()
    for r in rows:
        name = r["category__name"] or "Uncategorised"
        counts[name] = r["n"]

    return {
        "group_key": group_key,
        "label": group_key,
        "published_at": published_at,
        "counts": counts,
    }

def home(request):
    """
    Public landing OR signed-in dashboard:
      - If anonymous: show current marketing/CTA landing.
      - If logged in : show dashboard with Characters + Campaigns.
    """
    ctx = {
        "latest_patch": _get_latest_patch(),
    }
    latest_patch = PatchNote.objects.filter(is_published=True).order_by("-published_at", "-created_at").first()
    latest_patch = (
        PatchNote.objects
        .filter(is_published=True)
        .order_by("-published_at", "-created_at")
        .first()
    )

    latest_patch_counts = OrderedDict()
    if latest_patch:
        rows = (
            PatchChange.objects
            .filter(patch=latest_patch)
            .values("category__name")
            .annotate(n=Count("id"))
            .order_by("category__sort_order", "category__name")
        )
        for r in rows:
            latest_patch_counts[r["category__name"] or "Uncategorised"] = r["n"]    
    
    ctx.update({"latest_patch": latest_patch, "latest_patch_counts": latest_patch_counts})
    if request.user.is_authenticated:
        # Characters owned by the user
        my_chars = (
            Character.objects
            .filter(user=request.user)
            .order_by("-created_at", "-id")[:12]
        )


        # Campaign memberships (GM or player)
        memberships = (
            CampaignMembership.objects
            .select_related("campaign")
            .filter(user=request.user)
            .order_by("-campaign__created_at", "-campaign_id")
        )
        my_campaigns = [m.campaign for m in memberships]

        # Email verification meta (for banner)
        meta = getattr(request.user, "email_meta", None)

        ctx.update({
            "my_chars": my_chars,
            "my_campaigns": my_campaigns,
            "email_meta": meta,
                "latest_patch": latest_patch,
    "latest_patch_counts": latest_patch_counts,
        })
        return render(request, "home/dashboard.html", ctx)

    # anonymous landing (your current index copy)
    return render(request, "home/index.html", ctx)


def character_creator(request):
    return render(request, 'home/character_creator.html')  # Fix this path!


