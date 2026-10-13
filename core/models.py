from django.db import models


class SiteSettings(models.Model):
    """
    Singleton-style settings model. Create one row and edit it from admin.

    Controls site-wide display values like subscriber count.
    """

    subscriber_count_offset = models.IntegerField(
        default=0,
        help_text='Added to the real subscriber count on the homepage. '
                  'Set to 0 to show the true number. Use a positive number '
                  'to pad the count, or a negative one to reduce it.',
    )

    show_subscriber_count = models.BooleanField(
        default=True,
        help_text='Uncheck to hide the subscriber count entirely.',
    )

    subscriber_count_label = models.CharField(
        max_length=60,
        default='active subscribers',
        help_text='The text shown next to the number, e.g. "active subscribers".',
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return 'Site Settings'

    def save(self, *args, **kwargs):
        # Singleton: only ever one row
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Get or create the single settings row."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
