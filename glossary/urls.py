from django.urls import path
from .views import glossary_json

urlpatterns = [
    path("glossary.json", glossary_json, name="glossary_json"),
]
