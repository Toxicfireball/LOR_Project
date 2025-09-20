from django.contrib import admin
from .models import UserEmail, EmailVerification



@admin.register(UserEmail)
class UserEmailAdmin(admin.ModelAdmin):
    list_display = ("user", "is_verified")

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "purpose", "token", "created_at", "used_at")
    list_filter = ("purpose", "used_at")
