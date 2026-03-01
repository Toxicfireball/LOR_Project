from django.contrib import admin

# Register your models here.
# characters/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import AuditTrackedModel, ChangeCategory, ModelChangeLog
from django.http import HttpResponse
from django.urls import path
from django import forms
from .models import PatchNote, PatchChange
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
from django.contrib import admin


@admin.register(ModelChangeLog)
class ModelChangeLogAdmin(admin.ModelAdmin):
    list_display = (
        "occurred_at",
        "published_at",
        "publish_group",
        "action",
        "model_label",
        "object_repr",
        "changed_by",
        "is_published",
        "category",
    )
    list_filter = ("action", "is_published", "category", "content_type", "publish_group")
    search_fields = (
        "object_repr",
        "public_title",
        "public_summary",
        "public_body",
        "content_type__app_label",
        "content_type__model",
        "action",
        
)    
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
    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "<int:pk>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="characters_modelchangelog_preview",
            ),
        ]
        return extra + urls

    def preview_view(self, request, pk: int):
        obj = self.get_object(request, pk)
        if obj is None:
            return HttpResponse("Not found", status=404)
        # reuse your existing renderer (returns HTML table or "-"):contentReference[oaicite:3]{index=3}
        html = self.changes_pretty(obj)
        return HttpResponse(str(html), content_type="text/html")
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
        now = timezone.now()
        # mark published
        queryset.update(is_published=True)
        # set published_at only where missing
        queryset.filter(published_at__isnull=True).update(published_at=now)

    def unpublish_selected(self, request, queryset):
        # unpublish and clear published_at (matches your model save() behavior)
        queryset.update(is_published=False, published_at=None)



class PatchChangeInline(admin.TabularInline):
    model = PatchChange
    extra = 0
    autocomplete_fields = ("change_log",)  # searchable dropdown for the audit entry

    fields = (
        "change_log",
        "change_model",
        "change_object",
        "diff_preview",
        "category",
        "reason",
        "note",
        "sort_order",
    )
    readonly_fields = ("change_model", "change_object", "diff_preview")
    ordering = ("sort_order", "id")


    def change_model(self, obj):
        if not obj.change_log_id or not obj.change_log.content_type_id:
            return "-"
        ct = obj.change_log.content_type
        return f"{ct.app_label}.{ct.model}"

    def change_object(self, obj):
        return getattr(obj.change_log, "object_repr", "") or "-"

    def diff_preview(self, obj):
        """
        Show exact before/after from ModelChangeLog.changes
        """
        if not obj.change_log_id:
            return "-"
        changes = obj.change_log.changes or {}
        if not changes:
            return "-"
        rows = []
        for field, diff in changes.items():
            before = diff.get("before")
            after = diff.get("after")
            rows.append(
                f"<tr><td>{field}</td><td><code>{before}</code></td><td><code>{after}</code></td></tr>"
            )
        return format_html(
            "<table style='width:100%; border-collapse:collapse'>"
            "<thead><tr><th style='text-align:left'>Field</th><th style='text-align:left'>Before</th><th style='text-align:left'>After</th></tr></thead>"
            "<tbody>{}</tbody></table>",
            format_html("".join(rows)),
        )


@admin.register(PatchNote)
class PatchNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "published_at", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    inlines = (PatchChangeInline,)
    fieldsets = (
        ("Patch Note", {"fields": ("title", "slug", "summary", "body")}),
        ("Publishing", {"fields": ("is_published", "published_at")}),
    )