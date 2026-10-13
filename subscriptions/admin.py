from django.contrib import admin
from django.utils.html import format_html

from .models import Payment, Subscription, SubscriptionPlan
from datetime import timedelta

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .models import Payment, Subscription, SubscriptionPlan


# ------------------------------------------------------------------
# Subscription Plan
# ------------------------------------------------------------------

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'price',
        'price_display',
        'currency',
        'duration',
        'is_featured',
        'is_active',
        'sort_order',
    )
    list_filter = ('duration', 'is_active', 'is_featured', 'currency')
    list_editable = ('price', 'is_featured', 'is_active', 'sort_order')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('Identity', {'fields': ('name', 'slug', 'description')}),
        ('Pricing', {'fields': ('price', 'currency')}),
        ('Duration', {
            'fields': ('duration',),
            'description': 'Weekly = 7 days, Monthly = 30 days, 3 Months = 90 days.',
        }),
        ('Display', {'fields': ('is_featured', 'is_active', 'sort_order')}),
    )


# ------------------------------------------------------------------
# Subscription
# ------------------------------------------------------------------

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'plan',
        'status_badge',
        'start_date',
        'expiry_date',
        'days_remaining_display',
        'amount_paid',
        'created_at',
    )
    list_filter = ('status', 'plan', 'start_date')
    search_fields = ('user__username', 'user__email', 'payment_reference', 'notes')
    date_hierarchy = 'start_date'
    ordering = ('-start_date', '-created_at')
    list_per_page = 30

    readonly_fields = ('created_at', 'updated_at', 'days_remaining_display')
    autocomplete_fields = ('user',)

    fieldsets = (
        ('User & Plan', {'fields': ('user', 'plan')}),
        ('Period', {
            'fields': ('start_date', 'expiry_date', 'days_remaining_display'),
            'description': 'Set expiry_date to grant access until that date.',
        }),
        ('Payment', {
            'fields': ('amount_paid', 'currency', 'payment_reference'),
        }),
        ('Status', {
            'fields': ('status', 'notes'),
            'description': 'Status auto-flips to Expired when expiry_date passes. Set Cancelled to revoke access early.',
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'active': '#22c55e',
            'expired': '#8a8a95',
            'cancelled': '#ef4444',
        }
        color = colors.get(obj.status, '#8a8a95')
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;">'
            '<span style="width:9px;height:9px;border-radius:50%;background:{};'
            'box-shadow:0 0 6px {};"></span>'
            '<span style="font-weight:600;">{}</span>'
            '</span>',
            color, color, obj.get_status_display()
        )

    @admin.display(description='Days left')
    def days_remaining_display(self, obj):
        if not obj.pk:
            return '—'
        d = obj.days_remaining
        if d < 0:
            return f'{abs(d)} days ago'
        if d == 0:
            return 'expires today'
        return f'{d} days'


# ------------------------------------------------------------------
# Payment
# ------------------------------------------------------------------

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'user',
        'amount_display',
        'provider',
        'status_badge',
        'paid_at',
        'created_at',
    )
    list_filter = ('status', 'provider', 'created_at')
    search_fields = ('reference', 'user__username', 'user__email')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 30

    readonly_fields = ('reference', 'created_at', 'updated_at', 'paid_at')
    autocomplete_fields = ('user',)

    fieldsets = (
        ('Who', {'fields': ('user', 'plan', 'subscription')}),
        ('Money', {'fields': ('amount', 'currency')}),
        ('Provider', {
            'fields': ('provider', 'reference', 'status'),
            'description': 'Reference is auto-generated if left blank.',
        }),
        ('Timing', {'fields': ('paid_at', 'created_at', 'updated_at')}),
        ('Debug', {
            'fields': ('raw_response',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Amount')
    def amount_display(self, obj):
        return f'{obj.currency} {obj.amount:,.2f}'

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'pending': '#eab308',
            'success': '#22c55e',
            'failed': '#ef4444',
            'refunded': '#8a8a95',
        }
        color = colors.get(obj.status, '#8a8a95')
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;">'
            '<span style="width:9px;height:9px;border-radius:50%;background:{};'
            'box-shadow:0 0 6px {};"></span>'
            '<span style="font-weight:600;">{}</span>'
            '</span>',
            color, color, obj.get_status_display()
        )
        # --------------------------------------------------------------
    # Admin actions
    # --------------------------------------------------------------

    actions = ['activate_selected']

    @admin.action(description='Activate subscription for selected user')
    def activate_selected(self, request, queryset):
        """
        Not used on the record level — this action is designed to work with
        a user + plan already set. See the bulk helper below.
        """
        messages.info(
            request,
            'To activate a subscription: click "Add subscription", pick the user and plan, '
            'and the start/expiry dates will be filled in automatically.'
        )

    def get_changeform_initial_data(self, request):
        """
        Pre-fill the add form with sensible defaults so activation is fast.
        """
        return {
            'start_date': timezone.localdate(),
            'status': Subscription.STATUS_ACTIVE,
        }

    def save_model(self, request, obj, form, change):
        """
        If the admin doesn't set an expiry date and a plan is chosen,
        compute it automatically from the plan's duration.
        """
        if obj.plan and not obj.expiry_date:
            obj.expiry_date = obj.start_date + timedelta(days=obj.plan.duration_days)
        if not obj.amount_paid:
            obj.amount_paid = obj.plan.price if obj.plan else 0
        if not obj.currency and obj.plan:
            obj.currency = obj.plan.currency
        super().save_model(request, obj, form, change)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """
        Make expiry_date optional in the admin so the auto-fill in save_model can kick in.
        """
        if db_field.name == 'expiry_date':
            kwargs['required'] = False
        return super().formfield_for_dbfield(db_field, request, **kwargs)
