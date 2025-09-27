from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch

# import your models
from characters.models import Character
from campaigns.models import Campaign, CampaignMembership

def home(request):
    """
    Public landing OR signed-in dashboard:
      - If anonymous: show current marketing/CTA landing.
      - If logged in : show dashboard with Characters + Campaigns.
    """
    ctx = {}
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
        })
        return render(request, "home/dashboard.html", ctx)

    # anonymous landing (your current index copy)
    return render(request, "home/index.html", ctx)


def character_creator(request):
    return render(request, 'home/character_creator.html')  # Fix this path!


