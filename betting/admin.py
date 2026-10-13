from datetime import date

from django.contrib import admin
from django.utils.html import format_html

from .models import BetCode
from .models import BettingPlatform  # add near the top with other imports


class TodayFilter(admin.SimpleListFilter):
    """Adds a 'Today only' shortcut to the right sidebar."""
    title = 'show'
    parameter_name = 'show'

    def lookups(self, request, model_admin):
        return (
            ('today', 'Today only'),
            ('week', 'Last 7 days'),
            ('all', 'All time'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'today':
            return queryset.filter(pick_date=date.today())
        if value == 'week':
            return queryset.filter(pick_date__gte=date.today() - __import__('datetime').timedelta(days=7))
        return queryset


@admin.register(BetCode)
class BetCodeAdmin(admin.ModelAdmin):
    """Admin workflow for daily betting codes."""

    list_display = (
        'pick_date',
        'title',
        'result_badge',
        'result',
        'odds',
        'is_published',
        'created_at',
    )

    list_filter = (
        TodayFilter,
        'result',
        'is_published',
    )

    search_fields = (
        'title',
        'code',
        'description',
    )

    date_hierarchy = 'pick_date'

    ordering = ('-pick_date', '-created_at')

    list_editable = (
        'result',
        'is_published',
    )

    list_per_page = 30

    fieldsets = (
        ('Pick details', {
            'fields': ('title', 'code', 'odds', 'description')
        }),
        ('Scheduling', {
            'fields': ('pick_date', 'is_published'),
            'description': 'Pick date defaults to today. Uncheck "is published" to hide the pick from the public site.'
        }),
        ('Result', {
            'fields': ('result',),
            'description': 'Set to Pending until the matches finish, then update to Won or Lost.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Status')
    def result_badge(self, obj):
        colors = {
            'pending': '#eab308',
            'won': '#22c55e',
            'lost': '#ef4444',
        }
        color = colors.get(obj.result, '#8a8a95')
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;">'
            '<span style="width:9px;height:9px;border-radius:50%;background:{};'
            'box-shadow:0 0 6px {};"></span>'
            '<span style="font-weight:600;">{}</span>'
            '</span>',
            color, color, obj.get_result_display()
        )
@admin.register(BettingPlatform)
class BettingPlatformAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'logo_thumb',
        'url_short',
        'description',
        'is_featured',
        'is_active',
        'sort_order',
    )
    list_filter = ('is_active', 'is_featured')
    list_editable = ('is_featured', 'is_active', 'sort_order')
    search_fields = ('name', 'description', 'url')
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('Identity', {'fields': ('name', 'slug', 'description', 'bonus_note')}),
        ('Branding', {
            'fields': ('logo',),
            'description': 'PNG or SVG. Transparent background strongly preferred.',
        }),
        ('Link', {
            'fields': ('url',),
            'description': 'Use your affiliate referral link here if you have one.',
        }),
        ('Display', {'fields': ('is_featured', 'is_active', 'sort_order')}),
    )

    @admin.display(description='Logo')
    def logo_thumb(self, obj):
        if not obj.logo:
            return '—'
        return format_html(
            '<img src="{}" style="height:32px;width:auto;border-radius:4px;background:#14141a;padding:3px;" />',
            obj.logo.url,
        )

    @admin.display(description='URL')
    def url_short(self, obj):
        return (obj.url[:50] + '…') if obj.url and len(obj.url) > 50 else obj.url