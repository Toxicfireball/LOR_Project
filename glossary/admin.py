from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import GlossaryTerm

@admin.register(GlossaryTerm)
class GlossaryTermAdmin(admin.ModelAdmin):
    list_display = ("term", "active", "priority", "case_sensitive", "whole_word")
    list_filter = ("active", "case_sensitive", "whole_word")
    search_fields = ("term", "aliases", "definition")
