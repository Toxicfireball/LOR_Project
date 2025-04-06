# characters/forms.py

from django import forms
from .models import Character


class CharacterCreationStage1Form(forms.ModelForm):
    class Meta:
        model = Character
        fields = [
            'name',
            'race',
            'background',
            'backstory',
            'strength',
            'dexterity',
            'constitution',
            'intelligence',
            'wisdom',
            'charisma',
        ]
        widgets = {
            # The ability scores are controlled by your JavaScript, so we hide them.
            'strength': forms.HiddenInput(),
            'dexterity': forms.HiddenInput(),
            'constitution': forms.HiddenInput(),
            'intelligence': forms.HiddenInput(),
            'wisdom': forms.HiddenInput(),
            'charisma': forms.HiddenInput(),
        }
