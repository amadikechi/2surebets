from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from betting.models import BetCode


class StaticViewSitemap(Sitemap):
    """The main static pages."""
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return [
            ('core:home', 1.0, 'daily'),
            ('betting:picks', 0.9, 'daily'),
            ('betting:results', 0.9, 'daily'),
            ('subscriptions:pricing', 0.8, 'monthly'),
            ('core:about', 0.6, 'monthly'),
            ('core:contact', 0.5, 'monthly'),
            ('core:terms', 0.3, 'yearly'),
            ('core:privacy', 0.3, 'yearly'),
        ]

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]


class BetCodeSitemap(Sitemap):
    """Individual settled picks."""
    priority = 0.6
    changefreq = 'monthly'
    protocol = 'https'

    def items(self):
        return BetCode.objects.filter(
            is_published=True,
        ).exclude(result=BetCode.RESULT_PENDING).order_by('-pick_date')[:500]

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        # We don't have individual detail pages yet, so point to the results page.
        # When you add per-pick pages, change this to reverse('betting:pick_detail', args=[obj.pk])
        return reverse('betting:results') + f'?date={obj.pick_date.isoformat()}'