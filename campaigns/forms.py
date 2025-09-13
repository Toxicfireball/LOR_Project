from django import forms
from .models import Campaign
from characters.models import Character

class CampaignCreationForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "e.g. The Shattered Isles",
                "class": "form-control"
            }),
            "description": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Campaign premise, tone, house rules, session cadence, safety tools…",
                "class": "form-control"
            }),
        }
        help_texts = {
            "name": "A short, memorable name players will recognize.",
            "description": "Give players context: elevator pitch, starting level, allowed sources, expectations.",
        }

class CharacterChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        owner = getattr(obj.user, "username", "unknown")
        lvl = getattr(obj, "level", 0) or 0
        return f"{obj.name} — {owner} (Level {lvl})"

class AttachCharacterForm(forms.Form):
    character = CharacterChoiceField(
        queryset=Character.objects.none(),
        label="Attach a character",
        empty_label="— Search your character —",
        widget=forms.Select(attrs={"class": "form-select", "data-enhanced": "tomselect"})
    )

    def __init__(self, *args, user=None, campaign=None, is_gm=False, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Character.objects.filter(campaign__isnull=True) | Character.objects.filter(campaign=campaign)
        if not is_gm:
            qs = qs.filter(user=user)
        self.fields["character"].queryset = qs.select_related("user").order_by("user__username", "name")
        self.fields["character"].help_text = (
            "Players: you can attach your own characters. "
            "GMs: you can attach anyone’s unassigned character."
        )
