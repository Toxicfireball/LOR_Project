# campaigns/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Campaign, CampaignMembership
from .forms import CampaignCreationForm
from django.shortcuts import get_object_or_404, render

@login_required
def campaign_list(request):
    # List all campaigns (you might later want to filter or paginate)
    campaigns = Campaign.objects.all()
    return render(request, 'campaigns/campaign_list.html', {'campaigns': campaigns})
@login_required
# views.py


def campaign_detail(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    # Compute membership here
    is_member = campaign.members.filter(id=request.user.id).exists()
    memberships = campaign.campaignmembership_set.all()


    context = {
        'campaign': campaign,
        'memberships': memberships,
        'is_member': is_member,
    }
    return render(request, 'campaigns/campaign_detail.html', context)
@login_required
def join_campaign(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    # Prevent duplicate membership:
    if not CampaignMembership.objects.filter(user=request.user, campaign=campaign).exists():
        CampaignMembership.objects.create(user=request.user, campaign=campaign, role='pc')
    return redirect('campaigns:campaign_detail', campaign_id=campaign.id)
@login_required
def create_campaign(request):
    if request.method == 'POST':
        form = CampaignCreationForm(request.POST)
        if form.is_valid():
            campaign = form.save()
            # Automatically add the current user as the Game Master (GM)
            CampaignMembership.objects.create(user=request.user, campaign=campaign, role='gm')
            return redirect('campaigns:campaign_detail', campaign_id=campaign.id)
    else:
        form = CampaignCreationForm()
    return render(request, 'campaigns/create_campaign.html', {'form': form})
