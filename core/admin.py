from django.contrib import admin

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'subscriber_count_offset',
        'show_subscriber_count',
        'updated_at',
    )

    fieldsets = (
        ('Subscriber count', {
            'fields': (
                'show_subscriber_count',
                'subscriber_count_offset',
                'subscriber_count_label',
            ),
            'description': (
                'The homepage subscriber count is: real active subscribers '
                '+ the offset below. Set the offset to 0 to show the true number.'
            ),
        }),
    )

    def has_add_permission(self, request):
        # Only one settings row ever exists
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
