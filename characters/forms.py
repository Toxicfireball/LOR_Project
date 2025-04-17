# forms.py
import json
from django import forms
from .models import Character

# Define a dictionary for the default skill proficiencies.
# In LOR, during character creation every skill is by default Trained.


class CharacterCreationForm(forms.ModelForm):
    """
    Form for creating a new character.
    This form collects basic information (name, race, subrace, background combo, etc.),
    ability scores (calculated via a point-buy system), a free-form backstory,
    and skill proficiencies (as a JSON string).
    
    The skill_proficiencies field is hidden from the user because it is computed
    from background selections and other bonuses. However, if no value is provided,
    we default all skills to "Trained".
    """


    class Meta:
        model = Character
        fields = [
            "name",
            "race",
            "subrace",
            "half_elf_origin",
            "bg_combo",
            "main_background",
            "side_background_1",
            "side_background_2",
            "backstory",
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        ]
        widgets = {
            "main_background": forms.Select(attrs={"id": "main_background", "name": "main_background"}),
            "side_background_1": forms.Select(attrs={"id": "side_background_1", "name": "side_background_1"}),
            "side_background_2": forms.Select(attrs={"id": "side_background_2", "name": "side_background_2"}),
            "backstory": forms.Textarea(attrs={"rows": 4, "cols": 40}),
            # Other fields may be rendered as hidden if handled entirely via JS.
        }

    def __init__(self, *args, **kwargs):
        """
        Initialize the form.
        You can set initial default values for ability scores here if needed.
        For example, set the base ability scores to 8.
        """
        super().__init__(*args, **kwargs)
        # Set initial ability scores for point-buy system.
        self.fields["strength"].initial = 8
        self.fields["dexterity"].initial = 8
        self.fields["constitution"].initial = 8
        self.fields["intelligence"].initial = 8
        self.fields["wisdom"].initial = 8
        self.fields["charisma"].initial = 8

        # Optionally, if you want to default skill_proficiencies to the default dictionary,
        # you can set the initial value as a JSON string.

    def clean_skill_proficiencies(self):
        """
        Ensure the skill_proficiencies field returns a valid mapping.
        If the field is empty, we assign the default skill proficiencies.
        """
        data = self.cleaned_data.get("skill_proficiencies")
        if not data:
            # If nothing was provided, return the default mapping.
            return DEFAULT_SKILL_PROFICIENCIES
        try:
            proficiencies = json.loads(data)
            # Optionally, validate that all required skills are present.
            for skill in DEFAULT_SKILL_PROFICIENCIES:
                if skill not in proficiencies:
                    proficiencies[skill] = DEFAULT_SKILL_PROFICIENCIES[skill]
            return proficiencies
        except ValueError:
            raise forms.ValidationError("Invalid format for skill proficiencies. Please contact support.")

    def clean(self):
        """
        You can include additional cross-field validations here.
        For example, you could check that the total background bonus does not exceed a limit.
        """
        cleaned_data = super().clean()
        # Example: Ensure that if bg_combo is not "0", then side background selections are provided.
        bg_combo = cleaned_data.get("bg_combo")
        main_bg = cleaned_data.get("main_background")
        if bg_combo and bg_combo != "0":
            if not cleaned_data.get("side_background_1"):
                self.add_error("side_background_1", "This field is required for the selected background combination.")
            if bg_combo == "2" and not cleaned_data.get("side_background_2"):
                self.add_error("side_background_2", "This field is required when selecting 2 side backgrounds.")
        return cleaned_data
