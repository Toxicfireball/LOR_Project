from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from .models import GlossaryTerm

# Cache for 1 hour (adjust as needed)
@cache_page(60 * 15)
def glossary_json(request):
    items = (GlossaryTerm.objects
             .filter(active=True)
             .order_by("-priority", "term"))
    payload = []
    for t in items:
        payload.append({
            "aliases": t.terms_list(),   # list[str]
            "defn": t.definition,        # raw text; we'll escape in JS
            "cs": t.case_sensitive,      # bool
            "ww": t.whole_word,          # bool
        })
    return JsonResponse({"terms": payload})
