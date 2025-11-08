"""
URL configuration for LOR_Website project.
"""

from django.urls import path, include, re_path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Core apps
    path("", include("home.urls")),
    path("accounts/", include("accounts.urls")),
    path("campaigns/", include("campaigns.urls")),
    path("characters/", include("characters.urls")),
    path("summernote/", include("django_summernote.urls")),
    path("", include("glossary.urls")),

    # 3P admin urls — no top-level `import nested_admin` required
    path("_nested_admin/", include("nested_admin.urls")),
]

# Dev-only additions
if settings.DEBUG:
    # Serve media during development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Dev reload tool only in DEBUG (avoid import crash in prod)
    urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]
else:
    # If you *must* serve media in a non-DEBUG env (not recommended), keep it guarded
    from django.views.static import serve as dj_serve
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", dj_serve, {"document_root": settings.MEDIA_ROOT}),
    ]