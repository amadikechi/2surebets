from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.shortcuts import render
from django.utils import timezone

from .models import BetCode


def results(request):
    """
    Public results page. Every published pick — won, lost, pending.

    Filters:
      ?result=all|won|lost|pending
      ?range=7|30|90|month|all
    """
    today = timezone.localdate()

    # Base queryset: only published picks
    qs = BetCode.objects.filter(is_published=True)

    # --- Result filter ---
    result_filter = request.GET.get('result', 'all').lower()
    if result_filter in (BetCode.RESULT_WON, BetCode.RESULT_LOST, BetCode.RESULT_PENDING):
        qs = qs.filter(result=result_filter)
    else:
        result_filter = 'all'

    # --- Date range filter ---
    range_filter = request.GET.get('range', '30').lower()
    if range_filter == '7':
        since = today - timedelta(days=7)
        qs = qs.filter(pick_date__gte=since)
    elif range_filter == '30':
        since = today - timedelta(days=30)
        qs = qs.filter(pick_date__gte=since)
    elif range_filter == '90':
        since = today - timedelta(days=90)
        qs = qs.filter(pick_date__gte=since)
    elif range_filter == 'month':
        qs = qs.filter(pick_date__year=today.year, pick_date__month=today.month)
    else:
        range_filter = 'all'

    # --- Aggregate stats over the SAME filter window (before result filter) ---
    stat_qs = BetCode.objects.filter(is_published=True)
    if range_filter in ('7', '30', '90'):
        stat_qs = stat_qs.filter(pick_date__gte=today - timedelta(days=int(range_filter)))
    elif range_filter == 'month':
        stat_qs = stat_qs.filter(pick_date__year=today.year, pick_date__month=today.month)

    counts = stat_qs.aggregate(
        total=Count('id'),
        won=Count('id', filter=Q(result=BetCode.RESULT_WON)),
        lost=Count('id', filter=Q(result=BetCode.RESULT_LOST)),
        pending=Count('id', filter=Q(result=BetCode.RESULT_PENDING)),
        avg_odds=Avg('odds'),
    )
    settled = counts['won'] + counts['lost']
    win_rate = round((counts['won'] / settled) * 100, 1) if settled else 0

    stats = {
        'total': counts['total'],
        'won': counts['won'],
        'lost': counts['lost'],
        'pending': counts['pending'],
        'avg_odds': round(counts['avg_odds'], 2) if counts['avg_odds'] else None,
        'win_rate': win_rate,
    }

    context = {
        'picks': qs,
        'stats': stats,
        'result_filter': result_filter,
        'range_filter': range_filter,
        'today': today,
    }
    return render(request, 'betting/results.html', context)
def picks(request):
    """
    Public list of recent published picks. The code is NEVER passed to the
    template here — codes are only unlocked on the dashboard for active
    subscribers. Everyone sees the lock.
    """
    today = timezone.localdate()

    # Recent published picks. Newest first. Limit for performance.
    recent = (
        BetCode.objects
        .filter(is_published=True)
        .order_by('-pick_date', '-created_at')[:50]
    )

    todays_picks = (
        BetCode.objects
        .filter(is_published=True, pick_date=today)
        .order_by('-created_at')
    )

    context = {
        'todays_picks': todays_picks,
        'recent_picks': recent,
        'today': today,
    }
    return render(request, 'betting/picks.html', context)