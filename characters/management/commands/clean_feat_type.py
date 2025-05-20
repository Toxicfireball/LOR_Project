from django.core.management.base import BaseCommand
from characters.models import ClassFeat

class Command(BaseCommand):
    help = "Clean and standardize feat_type values in ClassFeat"

    def handle(self, *args, **kwargs):
        for feat in ClassFeat.objects.all():
            raw = feat.feat_type or ""
            cleaned = raw.lower().replace('/', ',').replace('\\', ',')
            parts = [p.strip().capitalize() for p in cleaned.split(',') if p.strip()]
            parts = ['General' if p == 'Racial' else p for p in parts]

            parts = sorted(set(parts), key=lambda x: ['General', 'Class', 'Skill'].index(x) if x in ['General', 'Class', 'Skill'] else x)
            feat.feat_type = ", ".join(parts)
            feat.save()

        self.stdout.write(self.style.SUCCESS("✅ Feat types standardized."))
