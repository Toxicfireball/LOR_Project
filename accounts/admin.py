from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Submission

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display    = ('submitter', 'content_type', 'object_id',
                       'status', 'created_at', 'reviewed_at', 'reviewer')
    list_filter     = ('status', 'content_type')
    search_fields   = ('submitter__username',)
    actions         = ('approve_selected', 'reject_selected')

    def approve_selected(self, request, queryset):
        for sub in queryset.filter(status=Submission.STATUS_PENDING):
            sub.approve(by_user=request.user)
        self.message_user(request, "Selected submissions approved.")
    approve_selected.short_description = "Approve selected"

    def reject_selected(self, request, queryset):
        for sub in queryset.filter(status=Submission.STATUS_PENDING):
            sub.reject(by_user=request.user)
        self.message_user(request, "Selected submissions rejected.")
    reject_selected.short_description = "Reject selected"
