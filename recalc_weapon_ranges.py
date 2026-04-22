import math
from django.db import transaction
from characters.models import Weapon


def ceil_to_5(value):
    if value is None:
        return None
    value = int(value)
    return int(math.ceil(value / 5.0) * 5)


@transaction.atomic
def run():
    updated = []
    skipped = []

    for w in Weapon.objects.all().iterator():
        # Clear melee ranges completely
        if w.range_type == Weapon.MELEE:
            changed = False
            if w.range_effective is not None:
                w.range_effective = None
                changed = True
            if w.range_suboptimal is not None:
                w.range_suboptimal = None
                changed = True
            if w.range_maximum is not None:
                w.range_maximum = None
                changed = True

            if changed:
                updated.append(w)
            continue

        # Ranged weapons need both endpoints
        if w.range_effective is None or w.range_maximum is None:
            skipped.append((w.id, w.name, w.range_effective, w.range_maximum))
            continue

        effective = ceil_to_5(w.range_effective)
        maximum = ceil_to_5(w.range_maximum)

        if maximum < effective:
            maximum = effective

        # 3.5 on a 0-10 scale = 35% of the interval
        raw_suboptimal = effective + (maximum - effective) * 0.35
        suboptimal = ceil_to_5(raw_suboptimal)

        # Clamp into valid band order
        if suboptimal < effective:
            suboptimal = effective
        if suboptimal > maximum:
            suboptimal = maximum

        changed = (
            w.range_effective != effective
            or w.range_suboptimal != suboptimal
            or w.range_maximum != maximum
        )

        if changed:
            w.range_effective = effective
            w.range_suboptimal = suboptimal
            w.range_maximum = maximum
            updated.append(w)

    if updated:
        Weapon.objects.bulk_update(
            updated,
            ["range_effective", "range_suboptimal", "range_maximum"],
            batch_size=500,
        )

    print(f"Updated {len(updated)} weapons.")
    print(f"Skipped {len(skipped)} weapons with missing endpoints.")
    if skipped:
        print("Skipped rows:")
        for row in skipped:
            print(row)


run()