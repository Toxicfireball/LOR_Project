from django.db import models

# Create your models here.
from django.db import models

class GlossaryTerm(models.Model):
    term = models.CharField(max_length=100, unique=True)
    definition = models.TextField()
    aliases = models.TextField(
        blank=True,
        help_text="Comma-separated aliases (e.g., On hit, onhit)."
    )
    case_sensitive = models.BooleanField(default=False)
    whole_word = models.BooleanField(
        default=True,
        help_text="Match whole words only (recommended)."
    )
    active = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(
        default=0,
        help_text="Higher runs first; prefer longer/important terms."
    )

    def __str__(self):
        return self.term

    def terms_list(self):
        """base term + aliases as a unique, trimmed list"""
        base = [self.term.strip()]
        extra = [a.strip() for a in self.aliases.split(",") if a.strip()]
        seen, out = set(), []
        for w in base + extra:
            if w and w not in seen:
                out.append(w); seen.add(w)
        return out
