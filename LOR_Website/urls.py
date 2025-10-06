"""
URL configuration for LOR_Website project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path, include, re_path

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
import nested_admin
urlpatterns = [] 
if not settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', dj_serve, {'document_root': settings.MEDIA_ROOT}),
    ]
else:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
      path("_nested_admin/", include("nested_admin.urls")),
    path("admin/", admin.site.urls),
    path('', include('home.urls')),  
    path('accounts/', include('accounts.urls')),   # User auth URLs
    path('campaigns/', include('campaigns.urls')),   # Campaign system URLs (we’ll create these next)
    path('characters/', include('characters.urls')),
    path("__reload__/", include("django_browser_reload.urls")),
    path('summernote/', include('django_summernote.urls')),
        path("", include("glossary.urls")),
]


