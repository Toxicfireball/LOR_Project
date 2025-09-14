# campaigns/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from .models import Campaign, CampaignNote, CampaignMessage
from characters.models import Character, Weapon, Armor, SpecialItem


# ===== Helper: build a single "equipment" select =====
def equipment_choices():
    opts = []
    for w in Weapon.objects.order_by("name").values("id", "name"):
        opts.append((f"weapon:{w['id']}", f"Weapon – {w['name']}"))
    for a in Armor.objects.order_by("name").values("id", "name"):
        opts.append((f"armor:{a['id']}", f"Armor – {a['name']}"))
    for s in SpecialItem.objects.order_by("name").values("id", "name"):
        opts.append((f"specialitem:{s['id']}", f"Special – {s['name']}"))
    return opts


class CampaignCreationForm(forms.ModelForm):
    join_password = forms.CharField(
        label="Join Password (optional)",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Leave blank for open table"})
    )
    class Meta:
        model  = Campaign
        fields = ["name", "description", "join_password"]
        widgets = {
            "name":        forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

class AttachCharacterForm(forms.Form):
    character = forms.ModelChoiceField(queryset=Character.objects.none(), empty_label="— Pick a character —")

    def __init__(self, *args, user=None, campaign=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["character"].queryset = (
            Character.objects
            .filter(user=user, campaign__isnull=True)
            .order_by("name")
        )


# campaigns/forms.py
from django import forms
from characters.models import Character

# campaigns/forms.py
from django import forms
from characters.models import Character

class JoinCampaignForm(forms.Form):
    # Password only required if the campaign is locked (handled in __init__)
    password = forms.CharField(
        label="Password",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm "
                         "placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 "
                         "focus:border-indigo-500"
            }
        ),
    )

    # Optional: attach a character immediately when joining
    character = forms.ModelChoiceField(
        label="Attach a character (optional)",
        required=False,
        queryset=Character.objects.none(),
        empty_label="— Select a character (optional) —",
        widget=forms.Select(
            attrs={
                "class": "block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm "
                         "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            }
        ),
    )

    def __init__(self, *args, user=None, campaign=None, **kwargs):
        super().__init__(*args, **kwargs)
        # show only this user's unattached characters
        qs = Character.objects.filter(user=user, campaign__isnull=True).order_by("name") if user else Character.objects.none()
        self.fields["character"].queryset = qs

        # require password only when the campaign is locked
        if campaign and campaign.join_password:
            self.fields["password"].required = True


# campaigns/forms.py
from django import forms
from .models import CampaignNote
from characters.models import SpecialItem  # or whatever model your party items come from

class CampaignNoteForm(forms.ModelForm):
    class Meta:
        model = CampaignNote
        fields = ["visibility", "content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, user=None, campaign=None, is_gm=False, **kwargs):
        super().__init__(*args, **kwargs)
        if is_gm:
            self.fields["equipment"] = forms.ModelChoiceField(
                queryset=SpecialItem.objects.order_by("name"),
                required=False,
                label="Give item to party",
            )
            self.fields["quantity"] = forms.IntegerField(
                min_value=1, initial=1, required=False, label="Quantity"
            )

# campaigns/forms.py
from django import forms
from .models import CampaignNote
from characters.models import SpecialItem

class CampaignNoteForm(forms.Form):
    VIS_CHOICES = (("party","Party"), ("gm","GM only"))
    visibility = forms.ChoiceField(choices=VIS_CHOICES)
    content    = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}))

    # GM-only fields (dynamically added/removed)
    equipment  = forms.ModelChoiceField(
        queryset=SpecialItem.objects.order_by("name"),
        required=False,
        empty_label="— none —",
        label="Give item to party",
    )
    quantity   = forms.IntegerField(min_value=1, initial=1, required=False, label="Quantity")

    def __init__(self, *args, user=None, campaign=None, is_gm=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not is_gm:
            # hide GM fields entirely for players
            self.fields.pop("equipment")
            self.fields.pop("quantity")

class PartyItemForm(forms.Form):
    item = forms.ModelChoiceField(
        queryset=SpecialItem.objects.order_by("name"),
        label="Item",
        widget=forms.Select(attrs={
            "class": "block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        }),
    )
    quantity = forms.IntegerField(
        min_value=1, initial=1, label="Qty",
        widget=forms.NumberInput(attrs={
            "class": "block w-24 rounded-md border border-gray-300 px-3 py-2 text-sm"
        }),
    )
class MessageForm(forms.Form):
    recipient = forms.ModelChoiceField(queryset=User.objects.none(), widget=forms.Select(attrs={"class":"form-select"}))
    content   = forms.CharField(widget=forms.Textarea(attrs={"class":"form-control", "rows":6}))

    def __init__(self, *args, campaign=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        members = campaign.members.exclude(pk=user.pk) if campaign else User.objects.none()
        self.fields["recipient"].queryset = members.order_by("username")

# ===== Small utility for parsing equipment key =====
def parse_equipment_key(key: str):
    """
    'weapon:5' | 'armor:12' | 'specialitem:7' → (ContentType, pk)
    """
    if not key:
        return None, None
    kind, sid = key.split(":")
    sid = int(sid)
    model_map = {"weapon": Weapon, "armor": Armor, "specialitem": SpecialItem}
    model = model_map.get(kind)
    if not model:
        return None, None
    ctype = ContentType.objects.get_for_model(model)
    return ctype, sid
