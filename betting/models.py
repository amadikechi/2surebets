from django.db import models
from datetime import date
from django.db import models
from django.utils.text import slugify




class BetCode(models.Model):
    """
    A single daily betting pick published by the admin.

    The `code` field is the premium secret — it must only be shown
    to users with an active subscription.
    """

    RESULT_PENDING = 'pending'
    RESULT_WON = 'won'
    RESULT_LOST = 'lost'

    RESULT_CHOICES = [
        (RESULT_PENDING, 'Pending'),
        (RESULT_WON, 'Won'),
        (RESULT_LOST, 'Lost'),
    ]

    title = models.CharField(
        max_length=120,
        default='Daily Premium Code',
        help_text='Short label shown to users, e.g. "Daily Premium Code".'
    )

    code = models.CharField(
        max_length=64,
        help_text='The premium betting code (e.g. ABC123XYZ). Only visible to subscribers.',
    )

    odds = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text='Total odds for the pick, e.g. 8.50',
    )

    description = models.TextField(
        blank=True,
        help_text='Optional notes shown publicly (e.g. "EPL + La Liga mix").',
    )

    pick_date = models.DateField(
        default=date.today,
        help_text='The date this pick is for. Defaults to today.'
    )

    result = models.CharField(
        max_length=10,
        choices=RESULT_CHOICES,
        default=RESULT_PENDING,
        help_text='Set to Pending, Won, or Lost after matches finish.',
    )

    is_published = models.BooleanField(
        default=True,
        help_text='Uncheck to hide this pick from the public site.'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pick_date', '-created_at']
        verbose_name = 'Bet Code'
        verbose_name_plural = 'Bet Codes'

    def __str__(self):
        return f'{self.pick_date} — {self.title} ({self.get_result_display()})'

    @property
    def result_emoji(self):
        return {
            self.RESULT_PENDING: '🟡',
            self.RESULT_WON: '🟢',
            self.RESULT_LOST: '🔴',
        }.get(self.result, '🟡')
class BettingPlatform(models.Model):
    """
    A bookmaker / betting platform shown on the homepage.

    You paste either a plain URL or an affiliate referral link.
    Clicking a card opens the link in a new tab.
    """

    name = models.CharField(
        max_length=80,
        help_text='Platform name, e.g. "Bet9ja", "SportyBet".',
    )
    slug = models.SlugField(
        max_length=80,
        unique=True,
        blank=True,
        help_text='URL-safe ID. Auto-fills from name if left blank.',
    )
    logo = models.ImageField(
        upload_to='platforms/',
        blank=True,
        null=True,
        help_text='PNG or SVG with transparent background preferred.',
    )
    url = models.URLField(
        max_length=500,
        help_text='Full URL. Use your affiliate link if you have one.',
    )
    description = models.CharField(
        max_length=140,
        blank=True,
        help_text='One short line, e.g. "Nigeria\'s biggest bookmaker".',
    )
    bonus_note = models.CharField(
        max_length=80,
        blank=True,
        help_text='Optional highlight, e.g. "100% welcome bonus".',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Uncheck to hide from the site.',
    )
    is_featured = models.BooleanField(
        default=False,
        help_text='Show with a gold border ("Top pick").',
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text='Lower numbers appear first.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Betting Platform'
        verbose_name_plural = 'Betting Platforms'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
