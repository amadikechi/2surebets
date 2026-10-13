from django.contrib import admin

from .models import EmailVerification, NotificationLog, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'email_verified', 'email_notifications', 'whatsapp_notifications')
    list_filter = ('email_verified', 'email_notifications', 'whatsapp_notifications')
    search_fields = ('user__username', 'user__email', 'phone_number')
    list_editable = ('email_verified', 'email_notifications', 'whatsapp_notifications')
    autocomplete_fields = ('user',)


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'verified_at', 'is_verified', 'is_expired')
    search_fields = ('user__username', 'user__email', 'token')
    readonly_fields = ('user', 'token', 'created_at', 'verified_at')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel', 'status', 'subject', 'created_at')
    list_filter = ('channel', 'status', 'created_at')
    search_fields = ('user__username', 'user__email', 'subject', 'error')
    readonly_fields = ('user', 'channel', 'status', 'subject', 'body_preview', 'error', 'related_betcode', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
