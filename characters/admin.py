from django.contrib import admin

# Register your models here.
# characters/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import AuditTrackedModel, ChangeCategory, ModelChangeLog


@admin.register(AuditTrackedModel)
class AuditTrackedModelAdmin(admin.ModelAdmin):
    list_display = ("model_label", "enabled", "track_creates", "track_updates", "track_deletes", "track_m2m")
    list_editable = ("enabled", "track_creates", "track_updates", "track_deletes", "track_m2m")
    search_fields = ("content_type__app_label", "content_type__model")

    def model_label(self, obj):
        return f"{obj.content_type.app_label}.{obj.content_type.model}"


@admin.register(ChangeCategory)
class ChangeCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "sort_order")
    list_editable = ("sort_order",)
    search_fields = ("name", "slug")


@admin.register(ModelChangeLog)
class ModelChangeLogAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "action", "model_label", "object_repr", "changed_by", "is_published", "category")
    list_filter = ("action", "is_published", "category", "content_type")
    search_fields = ("object_repr", "reason", "public_title", "public_summary", "public_body")
    date_hierarchy = "occurred_at"

    readonly_fields = ("occurred_at", "content_type", "object_id", "object_link", "action", "changed_by", "request_path", "changes_pretty")

    fieldsets = (
        ("What changed", {
            "fields": ("occurred_at", "action", "content_type", "object_id", "object_link", "object_repr", "changed_by", "request_path", "changes_pretty")
        }),
        ("Internal notes", {
            "fields": ("reason",),
        }),
        ("Publish to website", {
            "fields": ("is_published", "published_at", "publish_group", "category", "public_title", "public_summary", "public_body"),
        }),
    )

    actions = ("publish_selected", "unpublish_selected")

    def model_label(self, obj):
        return f"{obj.content_type.app_label}.{obj.content_type.model}"

    def object_link(self, obj):
        Model = obj.content_type.model_class()
        if not Model:
            return "-"
        try:
            url = reverse(f"admin:{Model._meta.app_label}_{Model._meta.model_name}_change", args=[obj.object_id])
            return format_html('<a href="{}">Open object</a>', url)
        except Exception:
            return "-"

    def changes_pretty(self, obj):
        rows = []
        for field, diff in (obj.changes or {}).items():
            rows.append(
                f"<tr><td>{field}</td><td><code>{diff.get('before')}</code></td><td><code>{diff.get('after')}</code></td></tr>"
            )
        if not rows:
            return "-"
        return format_html(
            "<table style='width:100%; border-collapse:collapse'>"
            "<thead><tr><th style='text-align:left'>Field</th><th style='text-align:left'>Before</th><th style='text-align:left'>After</th></tr></thead>"
            "<tbody>{}</tbody></table>",
            format_html("".join(rows)),
        )

    def publish_selected(self, request, queryset):
        queryset.update(is_published=True)

    def unpublish_selected(self, request, queryset):
        queryset.update(is_published=False)
