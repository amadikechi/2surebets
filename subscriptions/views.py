from django.shortcuts import render

from .models import SubscriptionPlan


def pricing(request):
    """
    Public pricing page. Reads plans from the database.
    """
    plans = SubscriptionPlan.objects.filter(is_active=True)

    context = {
        'plans': plans,
    }
    return render(request, 'subscriptions/pricing.html', context)
