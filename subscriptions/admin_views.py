from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils import timezone

from .models import Subscription


@staff_member_required
def active_subscribers(request):
    """
    Simple staff-only page listing every currently active subscriber.
    Reachable at /admin/active-subscribers/
    """
    today = timezone.localdate()

    subs = (
        Subscription.objects
        .filter(
            status=Subscription.STATUS_ACTIVE,
            expiry_date__gte=today,
        )
        .select_related('user', 'plan')
        .order_by('expiry_date')
    )

    context = {
        'subs': subs,
        'total': subs.count(),
        'today': today,
        'title': 'Active subscribers',
    }
    return render(request, 'subscriptions/admin_active.html', context)