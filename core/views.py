from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from betting.models import BetCode, BettingPlatform
from subscriptions.models import get_display_subscriber_count


# ==================================================================
# HOME
# ==================================================================

def home(request):
    """
    Homepage: hero + today's picks + platforms + 30-day record + subscriber count.
    """
    today = timezone.localdate()
    thirty_days_ago = today - timedelta(days=30)

    published = BetCode.objects.filter(is_published=True)

    # --- Today's picks (fallback to last 3 if none today) ---
    todays_picks = published.filter(pick_date=today)
    if not todays_picks.exists():
        todays_picks = published[:3]

    # --- Stats for hero panel ---
    today_qs = published.filter(pick_date=today)
    today_stats = {
        'total': today_qs.count(),
        'pending': today_qs.filter(result=BetCode.RESULT_PENDING).count(),
        'avg_odds': today_qs.aggregate(a=Avg('odds'))['a'] or None,
    }
    if today_stats['avg_odds'] is not None:
        today_stats['avg_odds'] = round(today_stats['avg_odds'], 2)

    # --- Track record (last 30 days) ---
    recent = published.filter(pick_date__gte=thirty_days_ago)
    counts = recent.aggregate(
        total=Count('id'),
        won=Count('id', filter=Q(result=BetCode.RESULT_WON)),
        lost=Count('id', filter=Q(result=BetCode.RESULT_LOST)),
        pending=Count('id', filter=Q(result=BetCode.RESULT_PENDING)),
    )
    settled = counts['won'] + counts['lost']
    win_rate = round((counts['won'] / settled) * 100, 1) if settled else 0

    stats = {
        'total_published': published.count(),
        'last_30_days': counts['total'],
        'won_30': counts['won'],
        'lost_30': counts['lost'],
        'pending_30': counts['pending'],
        'win_rate': win_rate,
    }

    # --- Recent results strip (excludes today) ---
    recent_results = (
        published
        .filter(pick_date__gte=thirty_days_ago)
        .exclude(pick_date=today)[:6]
    )

    # --- Betting platforms shown on the homepage ---
    platforms = BettingPlatform.objects.filter(is_active=True)

    # --- 30-day results table ---
    thirty_day_picks = (
        published
        .filter(pick_date__gte=thirty_days_ago)
        .order_by('-pick_date', '-created_at')
    )

    # --- Subscriber count for the homepage trust display ---
    subscriber_count = get_display_subscriber_count()

    return render(request, 'core/home.html', {
        'todays_picks': todays_picks,
        'recent_results': recent_results,
        'today': today,
        'stats': stats,
        'today_stats': today_stats,
        'platforms': platforms,
        'thirty_day_picks': thirty_day_picks,
        'subscriber_count': subscriber_count,
    })


# ==================================================================
# STATIC PAGES
# ==================================================================

def about(request):
    """Static about page."""
    return render(request, 'core/about.html')


def terms(request):
    """Static terms page."""
    return render(request, 'core/terms.html')


def privacy(request):
    """Static privacy page."""
    return render(request, 'core/privacy.html')


# ==================================================================
# CONTACT
# ==================================================================

def contact(request):
    """Contact page + form with honeypot and rate limiting."""
    if request.method == 'POST':
        # ---- Honeypot check ----
        if request.POST.get('website', '').strip():
            messages.success(request, 'Thanks — your message has been received.')
            return redirect('core:contact')

        # ---- Rate limit check ----
        ip = _get_client_ip(request)
        cache_key = f'contact_rate_{ip}'
        if cache.get(cache_key):
            messages.error(
                request,
                'You recently sent a message. Please wait a minute before trying again.',
            )
            return redirect('core:contact')

        # ---- Validate fields ----
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        message_text = (request.POST.get('message') or '').strip()

        errors = []
        if not name:
            errors.append('Please provide your name.')
        if not email or '@' not in email:
            errors.append('Please provide a valid email.')
        if not message_text or len(message_text) < 10:
            errors.append('Please provide a message (at least 10 characters).')
        if len(message_text) > 5000:
            errors.append('Your message is too long. Please keep it under 5000 characters.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect('core:contact')

        # ---- Send ----
        try:
            send_mail(
                subject=f'[2SURE Contact] Message from {name}',
                message=f'From: {name} <{email}>\n\n{message_text}',
                from_email=settings.SITE_SUPPORT_EMAIL,
                recipient_list=[settings.SITE_SUPPORT_EMAIL],
                fail_silently=False,
            )
            cache.set(cache_key, True, 60)
            messages.success(
                request,
                'Thanks — your message has been received. We usually reply within 24 hours.',
            )
            return redirect('core:contact')
        except Exception:
            messages.error(
                request,
                'Sorry, we could not send your message right now. Please email us directly.',
            )
            return redirect('core:contact')

    return render(request, 'core/contact.html')


def _get_client_ip(request):
    """Return the real client IP, handling proxies."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


# ==================================================================
# ROBOTS.TXT
# ==================================================================

def robots_txt(request):
    """Serve robots.txt dynamically."""
    lines = [
        'User-agent: *',
        'Disallow: /admin/',
        'Disallow: /accounts/dashboard/',
        'Disallow: /accounts/profile/',
        'Disallow: /accounts/login/',
        'Disallow: /accounts/register/',
        'Disallow: /accounts/password-reset/',
        'Allow: /',
        '',
        f'Sitemap: https://{settings.SITE_DOMAIN}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')