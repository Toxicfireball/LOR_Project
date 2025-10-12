# campaigns/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
import re
from .models import Campaign, CampaignNote, CampaignMessage
from characters.models import Character, Weapon, Armor, SpecialItem
from characters.models import Character, ClassFeat
from .models import EnemyType, EnemyAbility, Encounter, EncounterEnemy, EnemyTag
from django.db.models import Q
from django.forms.models import inlineformset_factory
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
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["character"].queryset = (
            Character.objects.filter(user=user, campaign__isnull=True).order_by("name")
            if user else Character.objects.none()
        )

# campaigns/forms.py
from django import forms
from characters.models import Character

# campaigns/forms.py
from django import forms
from characters.models import Character

class JoinCampaignForm(forms.Form):
    password = forms.CharField(
        label="Password",
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm "
                     "placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 "
                     "focus:border-indigo-500"
        }),
    )
    character = forms.ModelChoiceField(
        label="Attach a character (optional)",
        required=False,
        queryset=Character.objects.none(),
        empty_label="— Select a character (optional) —",
        widget=forms.Select(attrs={
            "class": "block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm "
                     "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        }),
    )
    def __init__(self, *args, user=None, campaign=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["character"].queryset = (
            Character.objects.filter(user=user, campaign__isnull=True).order_by("name")
            if user else Character.objects.none()
        )
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
    # Added dynamically for GMs in __init__
    def __init__(self, *args, user=None, campaign=None, is_gm=False, **kwargs):
        super().__init__(*args, **kwargs)
        if is_gm:
            self.fields["equipment"] = forms.ModelChoiceField(
                queryset=SpecialItem.objects.order_by("name"),
                required=False,
                empty_label="— none —",
                label="Give item to party",
            )
            self.fields["quantity"] = forms.IntegerField(
                min_value=1, initial=1, required=False, label="Quantity"
            )

# campaigns/forms.py
from django import forms
from characters.models import Character, ClassFeature

WORD_BOUNDARY = r'(^|,|\\s){}(,|\\s|$)'

def skill_feat_queryset():
    # Feat type contains the word “Skill” (case-insensitive), respecting commas/whitespace
    pattern = re.compile("Skill", re.IGNORECASE)
    return ClassFeature.objects.filter(
        Q(feat_type__iregex=WORD_BOUNDARY.format(re.escape("Skill")))
    ).order_by("name")


class AssignSkillFeatsForm(forms.Form):
    character = forms.ModelChoiceField(
        queryset=Character.objects.none(),
        required=False,
        label="Target Character",
    )
    feat1 = forms.ModelChoiceField(queryset=ClassFeat.objects.none(), label="Skill Feat #1")
    feat2 = forms.ModelChoiceField(queryset=ClassFeat.objects.none(), required=False, label="Skill Feat #2 (optional)")
    apply_to_all = forms.BooleanField(required=False, initial=False, label="Apply to all attached characters")

    def __init__(self, *args, campaign=None, **kwargs):
        super().__init__(*args, **kwargs)
        # limit target list to this campaign
        self.fields["character"].queryset = (
            campaign.characters.order_by("user__username", "name") if campaign else Character.objects.none()
        )
        # filter feats where feat_type tokenizes to include "Skill"
        self.fields["feat1"].queryset = ClassFeat.objects.filter(
            feat_type__iregex=WORD_BOUNDARY.format(re.escape("Skill"))
        ).order_by("name")
        self.fields["feat2"].queryset = self.fields["feat1"].queryset

    def clean(self):
        cleaned = super().clean()
        f1, f2 = cleaned.get("feat1"), cleaned.get("feat2")
        if not f1 and not f2:
            raise forms.ValidationError("Pick at least one Skill Feat.")
        if f1 and f2 and f1.pk == f2.pk:
            raise forms.ValidationError("The two Skill Feats must be different.")
        if not cleaned.get("apply_to_all") and not cleaned.get("character"):
            raise forms.ValidationError("Pick a target character (or tick ‘Apply to all’).")
        return cleaned

class PartyItemForm(forms.Form):
    item = forms.ModelChoiceField(queryset=SpecialItem.objects.none(), label="Item",
        widget=forms.Select(attrs={"class": "block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"}))
    quantity = forms.IntegerField(min_value=1, initial=1, label="Qty",
        widget=forms.NumberInput(attrs={"class": "block w-24 rounded-md border border-gray-300 px-3 py-2 text-sm"}))
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = SpecialItem.objects.order_by("name")

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
# campaigns/forms.py  (ADD)

from django import forms
from .models import EnemyType, EnemyAbility, Encounter, EncounterEnemy

class EnemyTypeForm(forms.ModelForm):
    class Meta:
        model = EnemyType
        fields = [
            "name","level","hp","armor","dodge","initiative",
            "str_score","dex_score","con_score","int_score","wis_score","cha_score",
            "will_save","reflex_save","fortitude_save","speed",
            "perception","stealth","athletics",
            "description","resistances",
        ]


# campaigns/forms.py
# keep this for the standalone "add ability" view
class EnemyAbilityForm(forms.ModelForm):
    class Meta:
        model = EnemyAbility
        fields = ["enemy_type", "ability_type", "action_cost", "title", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

# NEW: used by the inline formset (NO enemy_type here)
class EnemyAbilityInlineForm(forms.ModelForm):
    class Meta:
        model = EnemyAbility
        fields = ["ability_type", "action_cost", "title", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # allow “— (Passive/None)” empty option without throwing a required error
        if "action_cost" in self.fields:
            self.fields["action_cost"].required = False

# NEW: make the FK hidden field non-required so missing/blank FK won't block validation
from django.forms.models import BaseInlineFormSet
class _EnemyAbilityBaseInlineFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        fk_name = self.fk.name  # usually "enemy_type"
        if fk_name in form.fields:
            form.fields[fk_name].required = False  # <- key line

# IMPORTANT: do not pass `fields=` when you pass `form=...`
EnemyAbilityInlineFormSet = inlineformset_factory(
    parent_model=EnemyType,
    model=EnemyAbility,
    form=EnemyAbilityInlineForm,
    formset=_EnemyAbilityBaseInlineFormSet,  # <- use custom base
    extra=0,
    can_delete=True,
)

from .models import EncounterParticipant, DamageEvent


# AddParticipantForm
class AddParticipantForm(forms.Form):
    character  = forms.ModelChoiceField(
        queryset=Character.objects.none(),
        empty_label="— Pick a character —",
        label="Character",
        widget=forms.Select(attrs={"class": "block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"})
    )
    role = forms.ChoiceField(
        choices=(("pc","Player"),("ally","Ally")),
        initial="pc", label="Role",
        widget=forms.Select(attrs={"class": "block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"})
    )
    initiative = forms.IntegerField(
        required=False, label="Initiative",
        widget=forms.NumberInput(attrs={"class": "block w-24 rounded-md border border-gray-300 px-3 py-2 text-sm"})
    )
    def __init__(self, *args, campaign=None, encounter=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = campaign.characters.order_by("user__username", "name") if campaign else Character.objects.none()
        if encounter is not None:
            qs = qs.exclude(encounter_participations__encounter=encounter)
        self.fields["character"].queryset = qs

class SetParticipantInitiativeForm(forms.Form):
    participant_id = forms.IntegerField()
    initiative = forms.IntegerField()


class RecordDamageForm(forms.Form):
    """
    The ONLY way to change enemy HP:
    - amount: how much HP to remove
    - attacker: one of the campaign's players OR "other"
    - other_name: required only if attacker == "other"
    """
    ee_id = forms.IntegerField()
    amount = forms.IntegerField(min_value=1, label="Remove HP")
    attacker = forms.ChoiceField(choices=[], label="Who did it?")
    other_name = forms.CharField(required=False, max_length=80, label="Other (name)")

    def __init__(self, *args, campaign=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = []
        if campaign:
            choices = [(str(ch.id), f"{ch.user.username} – {ch.name}")
                       for ch in campaign.characters.order_by("user__username", "name")]
        choices.append(("other", "Other…"))
        self.fields["attacker"].choices = [("", "— Who dealt it? —")] + choices

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("attacker") == "other" and not (cleaned.get("other_name") or "").strip():
            raise forms.ValidationError("Enter a name for ‘Other’.")
        return cleaned



class RecordEnemyToPCDamageForm(forms.Form):
    attacker_ee_id = forms.IntegerField()
    target_character = forms.ModelChoiceField(queryset=Character.objects.none())
    amount = forms.IntegerField(min_value=1)
    note = forms.CharField(required=False, max_length=255)

    def __init__(self, *args, campaign=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target_character"].queryset = (
            campaign.characters.order_by("user__username", "name") if campaign else Character.objects.none()
        )

class UpdateEnemyNoteForm(forms.Form):
    ee_id = forms.IntegerField()
    notes = forms.CharField(required=False, max_length=255)

class EncounterForm(forms.ModelForm):
    class Meta:
        model = Encounter
        fields = ["name","description"]
        widgets = {"description": forms.Textarea(attrs={"rows":2})}


class AddEnemyToEncounterForm(forms.Form):
    enemy_type = forms.ModelChoiceField(queryset=EnemyType.objects.all(),
        widget=forms.Select(attrs={"class":"block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"}))
    side = forms.ChoiceField(choices=EncounterEnemy.SIDE, initial="enemy",
        widget=forms.Select(attrs={"class":"block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"}))
    count = forms.IntegerField(min_value=1, initial=1,
        widget=forms.NumberInput(attrs={"class":"block w-24 rounded-md border border-gray-300 px-3 py-2 text-sm"}))


from .models import EnemyType, Encounter  # already imported above for other forms

class QuickAddEnemyForm(forms.Form):
    encounter = forms.ModelChoiceField(queryset=Encounter.objects.none())
    enemy_type = forms.ModelChoiceField(queryset=EnemyType.objects.all())
    side = forms.ChoiceField(choices=EncounterEnemy.SIDE, initial="enemy")
    count = forms.IntegerField(min_value=1, initial=1)
    def __init__(self, *args, campaign=None, **kwargs):
        super().__init__(*args, **kwargs)
        if campaign is not None:
            self.fields["encounter"].queryset = campaign.encounters.all()




class EnemyTypeCreateForm(forms.ModelForm):
    SCOPE_CHOICES = (("campaign", "This campaign"), ("global", "Global"))
    scope = forms.ChoiceField(choices=SCOPE_CHOICES, initial="campaign")
    tags  = forms.ModelMultipleChoiceField(
        queryset=EnemyTag.objects.none(), required=False,
        widget=forms.SelectMultiple(attrs={"size": 6})
    )
    class Meta:
        model = EnemyType
        fields = [
            "name","level","hp","armor","dodge","initiative",
            "str_score","dex_score","con_score","int_score","wis_score","cha_score",
            "will_save","reflex_save","fortitude_save",
            "perception","stealth","athletics","speed",
            "description","resistances","category","tags",   # + category
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "resistances": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, campaign=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.campaign = campaign
        # when editing, reflect the instance's current scope instead of defaulting to "campaign"
        if self.instance and self.instance.pk:
            self.fields["scope"].initial = "global" if self.instance.campaign_id is None else "campaign"
    
    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.campaign = None if self.cleaned_data.get("scope") == "global" else self.campaign
        if commit:
            obj.save()
            self.save_m2m()
        return obj