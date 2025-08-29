# characters/services/mastery.py

from django.db.models import Count, Q
from characters.models import (
    ClassFeature, CharacterFeature, CharacterClassProgress,
    SubclassMasteryLevel, SubclassGroup, ClassSubclass
)

def modules_per_mastery(subclass: ClassSubclass) -> int:
    # per-subclass override → umbrella default → 2
    sub = (subclass.modular_rules or {}).get("modules_per_mastery")
    grp = (subclass.group.modular_rules or {}).get("modules_per_mastery") if subclass.group else None
    return sub or grp or 2

def unlocked_rank_cap(character, subclass: ClassSubclass) -> int:
    """Max rank allowed by class level vs group schedule."""
    group = subclass.group
    if not group:
        return 0
    # class level in THIS base class:
    prog = CharacterClassProgress.objects.filter(
        character=character, character_class=subclass.base_class
    ).first()
    cls_level = prog.levels if prog else 0

    unlocks = list(
        SubclassMasteryLevel.objects.filter(subclass_group=group)
        .values_list("rank", "unlock_level")
    )
    allowed = [r for (r, lvl) in unlocks if cls_level >= lvl]
    return max(allowed or [0])

def current_modules(character, subclass: ClassSubclass) -> int:
    return CharacterFeature.objects.filter(
        character=character,
        subclass=subclass,
        feature__scope="subclass_feat"
    ).count()

def computed_rank_from_modules(character, subclass: ClassSubclass) -> int:
    per = modules_per_mastery(subclass)
    return current_modules(character, subclass) // per

def effective_mastery_rank(character, subclass: ClassSubclass) -> int:
    """The rank the character can *use* right now (modules AND schedule)."""
    return min(computed_rank_from_modules(character, subclass),
               unlocked_rank_cap(character, subclass))

def rank3_already_taken(character, group: SubclassGroup) -> bool:
    limit = (group.modular_rules or {}).get("max_rank3_picks", 0)
    if not limit:
        return False
    taken = CharacterFeature.objects.filter(
        character=character,
        feature__subclass_group=group,
        feature__mastery_rank=3
    ).count()
    return taken >= limit

def available_modules(character, subclass: ClassSubclass):
    """Which subclass_feats are legal to pick at this moment."""
    group = subclass.group
    cap   = effective_mastery_rank(character, subclass)
    qs = ClassFeature.objects.filter(
        scope="subclass_feat",
        subclass_group=group,
        subclasses=subclass,
        mastery_rank__lte=cap
    )
    # optional: hide rank-3 choices if global cap reached
    if rank3_already_taken(character, group):
        qs = qs.exclude(mastery_rank=3)
    return qs
