# characters/admin_views.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from .utils import parse_formula  # your own parser

@require_GET
@csrf_exempt  # only in admin or protect via staff_member_required
def validate_formula(request):
    expr = request.GET.get('formula','').strip()
    try:
        parse_formula(expr)    # raise on syntax/error
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})
