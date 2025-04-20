# characters/utils.py

import re
import random
from django.core.exceptions import ValidationError
from .models import Character  # adjust the import if your model is elsewhere

# only allow these operators and tokens
_VALID_RE = re.compile(
    r'^\s*([\d+\-*/().\s]|[A-Za-z_]\w*|\d+d(?:4|6|8|10|12|20)|round\s+(?:up|down))+\s*$'
)
_DICE_RE = re.compile(r'(\d+)d(4|6|8|10|12|20)')      # match “2d6”, “1d10”, etc
_VAR_RE  = re.compile(r'\b([A-Za-z_]\w*)\b')            # match identifiers

def parse_formula(formula: str, character: Character) -> int:
    """
    Turn a string like "1d10+level" or "proficiency_modifier/2 round up"
    into an integer, looking up `level`, `proficiency_modifier`,
    any `<classname>_level`, saving throws, etc. on the given character.
    """

    f = formula.strip().lower()
    if not f:
        return 0

    # 1) Basic whitelist check
    if not _VALID_RE.match(f):
        raise ValidationError(f"Illegal characters in formula: {formula!r}")

    # 2) Roll all dice
    def _roll_dice(m):
        n, faces = int(m.group(1)), int(m.group(2))
        return str(sum(random.randint(1, faces) for _ in range(n)))
    f = _DICE_RE.sub(_roll_dice, f)

    # 3) Substitute variables
    def _var_replace(m):
        name = m.group(1)
        # map the name to an integer from the character
        # you can expand this mapping with any stats you need
        lookup = {
            "level": character.level,
                                    "reflex_save": character.reflex_save,
            "fortitude_save": character.fortitude_save,
            "will_save": character.will_save,
            "initiative": character.initiative,
            "perception": character.perception,
            "dodge": character.dodge,
            "spell_attack": character.spell_attack,
            "spell_dc": character.spell_dc,
            "weapon_attack": character.weapon_attack,
                "strength":     character.strength,
                    "hp": character.HP,               # provide these properties/fields
    "temp_hp": character.temp_HP,
    "dexterity":    character.dexterity,
    "constitution": character.constitution,
    "intelligence": character.intelligence,
    "wisdom":       character.wisdom,
    "charisma":     character.charisma,
        }
        # also pull in each class’s own level, e.g. fighter_level, wizard_level, etc:
        for prog in character.class_progress.all():
            lookup[f"{prog.character_class.name.lower()}_level"] = prog.levels

        if name not in lookup:
            raise ValidationError(f"Unknown variable in formula: {name!r}")
        return str(lookup[name])

    f = _VAR_RE.sub(_var_replace, f)

    # 4) Handle “round up” / “round down”
    # e.g. transform “… /2 round up” → “math.ceil(…/2)”
    # (import math inside the eval namespace)
    f = re.sub(r'round\s+up', 'ceil', f)
    f = re.sub(r'round\s+down', 'floor', f)

    # 5) Safe eval
    try:
        # only expose math.ceil/floor
        from math import ceil, floor
        result = eval(f, {"__builtins__": None}, {"ceil": ceil, "floor": floor})
    except Exception as e:
        raise ValidationError(f"Could not evaluate formula {formula!r}: {e}")

    return int(result)
