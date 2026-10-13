from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


# ==================================================================
# SUBSCRIPTION PLAN
# ==================================================================

class SubscriptionPlan(models.Model):
    """
    A purchasable subscription tier (Weekly, Monthly, 3 Months).

    Prices are stored here, never hardcoded in templates.
    """

    DURATION_WEEKLY = 'weekly'
    DURATION_MONTHLY = 'monthly'
    DURATION_QUARTERLY = 'quarterly'

    DURATION_CHOICES = [
        (DURATION_WEEKLY, 'Weekly (7 days)'),
        (DURATION_MONTHLY, 'Monthly (30 days)'),
        (DURATION_QUARTERLY, '3 Months (90 days)'),
    ]

    # Days granted per duration. Used to calculate expiry after payment.
    DURATION_DAYS = {
        DURATION_WEEKLY: 7,
        DURATION_MONTHLY: 30,
        DURATION_QUARTERLY: 90,
    }

    name = models.CharField(
        max_length=60,
        help_text='Display name, e.g. "Weekly", "Monthly", "3 Months".',
    )
    slug = models.SlugField(
        max_length=60,
        unique=True,
        help_text='URL-safe identifier. Auto-fills from name if left blank.',
        blank=True,
    )
    duration = models.CharField(
        max_length=20,
        choices=DURATION_CHOICES,
        help_text='How long the subscription lasts.',
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Price in your local currency, e.g. 5000.00',
    )
    currency = models.CharField(
        max_length=8,
        default='NGN',
        help_text='Currency code, e.g. NGN, USD.',
    )
    description = models.CharField(
        max_length=160,
        blank=True,
        help_text='Short line shown on the pricing card.',
    )
    is_featured = models.BooleanField(
        default=False,
        help_text='Highlight this plan with a gold border ("Most popular").',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Uncheck to hide this plan from the site.',
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text='Lower numbers appear first.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'price']
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

    def __str__(self):
        return f'{self.name} — {self.currency} {self.price}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def duration_days(self):
        """Number of days this plan grants."""
        return self.DURATION_DAYS.get(self.duration, 30)

    @property
    def price_display(self):
        """Nice formatted price for templates, e.g. '₦5,000'."""
        symbols = {'NGN': '₦', 'USD': '$', 'EUR': '€', 'GBP': '£'}
        symbol = symbols.get(self.currency, self.currency + ' ')
        try:
            if self.price == int(self.price):
                return f'{symbol}{int(self.price):,}'
        except (TypeError, ValueError):
            pass
        return f'{symbol}{self.price}'


# ==================================================================
# SUBSCRIPTION
# ==================================================================

class Subscription(models.Model):
    """
    A user's active or past subscription to a plan.

    Activation flow:
      1. User pays (or admin activates manually).
      2. A Subscription row is created with status ACTIVE and an expiry date.
      3. `is_valid` returns True until expiry, then the system treats it as expired.
    """

    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,   # don't delete a plan that has subscriptions
        related_name='subscriptions',
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Amount actually paid for this subscription.',
    )
    currency = models.CharField(
        max_length=8,
        default='NGN',
    )
    start_date = models.DateField(
        default=timezone.localdate,
        help_text='When the subscription began.',
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text='When the subscription stops granting access. Auto-filled from the plan if left blank.',
    )
    
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        help_text='Manual override. Auto-expires based on expiry_date.',
    )
    payment_reference = models.CharField(
        max_length=120,
        blank=True,
        help_text='Reference from the payment provider, if any.',
    )
    notes = models.CharField(
        max_length=240,
        blank=True,
        help_text='Internal notes — not shown to the user.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-created_at']
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        indexes = [
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f'{self.user.username} — {self.plan.name} ({self.status})'

    # ----- Computed helpers -----

    @property
    def is_expired_by_date(self):
        """True if today is past the expiry date. A blank expiry is never expired."""
        if not self.expiry_date:
            return False
        return timezone.localdate() > self.expiry_date

    @property
    def is_valid(self):
        """
        Single source of truth for 'does this subscription grant access?'
        Access is granted only when: status is ACTIVE and the expiry date is in the future.
        """
        return self.status == self.STATUS_ACTIVE and not self.is_expired_by_date

    @property
    def days_remaining(self):
        """Whole days left until expiry. Negative if already expired."""
        if not self.expiry_date:
            return 0
        return (self.expiry_date - timezone.localdate()).days

    def save(self, *args, **kwargs):
        """
        Auto-mark as EXPIRED when the expiry date has passed.
        This runs on every save so the admin list is always accurate,
        without needing a cron job (that comes later).
        """
        if self.status == self.STATUS_ACTIVE and self.is_expired_by_date:
            self.status = self.STATUS_EXPIRED
        super().save(*args, **kwargs)

    def extend_expiry(self, days):
        """Add days to the expiry date — used when stacking subscriptions."""
        base = self.expiry_date or timezone.localdate()
        self.expiry_date = base + timedelta(days=days)


# ==================================================================
# PAYMENT
# ==================================================================

class Payment(models.Model):
    """
    Every payment attempt, successful or not.

    Payments can exist without a subscription (e.g. failed attempts).
    Subscriptions can exist without a payment (e.g. admin-granted free access).
    """

    STATUS_PENDING = 'pending'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    PROVIDER_MANUAL = 'manual'
    PROVIDER_PAYSTACK = 'paystack'
    PROVIDER_FLUTTERWAVE = 'flutterwave'

    PROVIDER_CHOICES = [
        (PROVIDER_MANUAL, 'Manual / Admin'),
        (PROVIDER_PAYSTACK, 'Paystack'),
        (PROVIDER_FLUTTERWAVE, 'Flutterwave'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payments',
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text='The subscription this payment activated (if any).',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default='NGN')
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_MANUAL,
    )
    reference = models.CharField(
        max_length=120,
        unique=True,
        help_text='Unique reference. Auto-generated if left blank.',
    )
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the payment succeeded (if it did).',
    )
    raw_response = models.TextField(
        blank=True,
        help_text='Raw JSON from the payment provider. For debugging.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f'{self.reference} — {self.user.username} — {self.get_status_display()}'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()
        if self.status == self.STATUS_SUCCESS and not self.paid_at:
            self.paid_at = timezone.now()
        super().save(*args, **kwargs)

    def _generate_reference(self):
        """Generate a unique reference like TS-20261002-AB12CD."""
        import uuid
        stamp = timezone.localdate().strftime('%Y%m%d')
        token = uuid.uuid4().hex[:6].upper()
        return f'TS-{stamp}-{token}'


# ==================================================================
# HELPERS
# ==================================================================

def get_active_subscription(user):
    """
    Return the user's current valid subscription, or None.

    Used everywhere we need to check "does this user have access right now?"

    We also proactively mark expired subscriptions as expired when we touch them,
    so the admin stays accurate without needing a cron job.
    """
    if not user or not user.is_authenticated:
        return None

    today = timezone.localdate()

    # Touch any active-but-past-expiry subscriptions so their status updates
    stale = Subscription.objects.filter(
        user=user,
        status=Subscription.STATUS_ACTIVE,
        expiry_date__lt=today,
    )
    if stale.exists():
        stale.update(status=Subscription.STATUS_EXPIRED)

    return (
        Subscription.objects
        .filter(
            user=user,
            status=Subscription.STATUS_ACTIVE,
            expiry_date__gte=today,
        )
        .select_related('plan')
        .order_by('-expiry_date')
        .first()
    )
def get_active_subscriber_count():
    """
    Return the number of unique users with a currently valid subscription.

    A user is counted once, even if they have multiple active subscriptions.
    """
    today = timezone.localdate()

    # First, expire any stale subscriptions so the count is accurate
    Subscription.objects.filter(
        status=Subscription.STATUS_ACTIVE,
        expiry_date__lt=today,
    ).update(status=Subscription.STATUS_EXPIRED)

    return (
        Subscription.objects
        .filter(
            status=Subscription.STATUS_ACTIVE,
            expiry_date__gte=today,
        )
        .values('user_id')
        .distinct()
        .count()
    )


def get_display_subscriber_count():
    """
    Return the count shown on the homepage: real count + admin offset.

    Returns None if the count is hidden via SiteSettings.
    """
    from core.models import SiteSettings

    settings_obj = SiteSettings.load()
    if not settings_obj.show_subscriber_count:
        return None

    real = get_active_subscriber_count()
    total = real + settings_obj.subscriber_count_offset

    # Never show a negative number
    return max(total, 0)