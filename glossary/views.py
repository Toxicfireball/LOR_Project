from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.urls import reverse
from urllib.parse import urlencode
from .models import GlossaryTerm

@cache_page(60 * 15)
def glossary_json(request):
    items = (GlossaryTerm.objects
             .filter(active=True)
             .order_by("-priority", "term"))

    rb = request.GET.get("rb")  # optional rulebook id

    # Pick the glossary page to link to:
    # - if rb provided -> per-rulebook glossary
    # - else -> global glossary
    if rb and rb.isdigit():
        glossary_base = reverse("characters:rulebook_glossary", args=[int(rb)])
    else:
        glossary_base = reverse("characters:rulebooks_glossary")

    # Optional: rulebook search page (your RulebookListView supports q=...)
    rulebook_search = reverse("characters:rulebook_list")

    payload = []
    for t in items:
        q = urlencode({"q": t.term})

        # Your glossary.html uses: <div id="term-{{ t.pk }}">
        anchor = f"term-{t.pk}"

        payload.append({
            "id": t.pk,
            "term": t.term,
            "aliases": t.terms_list(),
            "defn": t.definition,
            "cs": t.case_sensitive,
            "ww": t.whole_word,

            # Link to glossary page, filtered + scrolled to the term
            "url": f"{glossary_base}?{q}#{anchor}",

            # Optional: link to rulebooks search results
            "search_url": f"{rulebook_search}?{q}",
        })

    return JsonResponse({"terms": payload})