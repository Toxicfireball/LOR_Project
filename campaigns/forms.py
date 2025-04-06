# campaigns/forms.py

from django import forms
from .models import Campaign

class CampaignCreationForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['name', 'description']
