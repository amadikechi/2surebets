import hashlib
import hmac
import json
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from subscriptions.models import Payment, Subscription, SubscriptionPlan

from .paystack import PaystackError, initialize_transaction, verify_transaction

logger = logging.getLogger(__name__)


# ==================================================================
# 1. INITIATE — user clicks Subscribe on /pricing/
# ==================================================================

@login_required
def initiate_payment(request, plan_slug):
    """
    Create a Paystack transaction and redirect the user to checkout.
    """
    plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)

    # Amount in kobo (smallest unit) — ₦1 = 100 kobo
    amount_kobo = int(plan.price * 100)

    # Unique reference — this is what we'll verify later
    reference = f'TS-{timezone.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:10].upper()}'

    # Where Paystack sends the user after successful payment
    callback_url = request.build_absolute_uri(reverse('payments:verify'))

    # Create the Payment record now, in PENDING state. It gets confirmed on verify.
    payment = Payment.objects.create(
        user=request.user,
        plan=plan,
        amount=plan.price,
        currency=plan.currency,
        provider=Payment.PROVIDER_PAYSTACK,
        reference=reference,
        status=Payment.STATUS_PENDING,
    )

    try:
        auth_url = initialize_transaction(
            email=request.user.email or f'{request.user.username}@2surebets.com',
            amount_kobo=amount_kobo,
            reference=reference,
            callback_url=callback_url,
            metadata={
                'user_id': request.user.id,
                'plan_slug': plan.slug,
                'payment_id': payment.id,
            },
        )
    except PaystackError as exc:
        logger.error('Payment init failed: %s', exc)
        payment.status = Payment.STATUS_FAILED
        payment.save()
        messages.error(request, 'We could not start the payment. Please try again.')
        return redirect('subscriptions:pricing')

    return redirect(auth_url)


# ==================================================================
# 2. VERIFY — user returns from Paystack
# ==================================================================

@login_required
def verify_payment(request):
    """
    Paystack redirects here after payment. We verify server-side.
    """
    reference = request.GET.get('reference') or request.GET.get('trxref')

    if not reference:
        messages.error(request, 'Missing payment reference.')
        return redirect('subscriptions:pricing')

    try:
        payment = Payment.objects.get(reference=reference, user=request.user)
    except Payment.DoesNotExist:
        messages.error(request, 'Payment record not found.')
        return redirect('subscriptions:pricing')

    # Already processed? Just show success.
    if payment.status == Payment.STATUS_SUCCESS:
        return render(request, 'payments/success.html', {'payment': payment})

    try:
        data = verify_transaction(reference)
    except PaystackError as exc:
        logger.error('Verify failed for %s: %s', reference, exc)
        payment.status = Payment.STATUS_FAILED
        payment.save()
        messages.error(request, 'We could not verify your payment. Contact support.')
        return redirect('subscriptions:pricing')

    # --- Verification checks ---
    status_ok = data.get('status') == 'success'
    amount_ok = int(data.get('amount', 0)) == int(payment.amount * 100)
    currency_ok = data.get('currency', '').upper() == payment.currency.upper()

    if not (status_ok and amount_ok and currency_ok):
        logger.warning(
            'Payment verification mismatch for %s — status=%s amount=%s currency=%s',
            reference, status_ok, amount_ok, currency_ok,
        )
        payment.status = Payment.STATUS_FAILED
        payment.raw_response = json.dumps(data)
        payment.save()
        return render(request, 'payments/failed.html', {'payment': payment})

    # --- Activate subscription ---
    payment.status = Payment.STATUS_SUCCESS
    payment.paid_at = timezone.now()
    payment.raw_response = json.dumps(data)
    payment.save()

    subscription = activate_subscription(
        user=request.user,
        plan=payment.plan,
        amount=payment.amount,
        reference=reference,
    )
    payment.subscription = subscription
    payment.save()

    messages.success(request, 'Payment successful. Your subscription is now active.')
    return render(request, 'payments/success.html', {
        'payment': payment,
        'subscription': subscription,
    })


# ==================================================================
# 3. ACTIVATION helper — shared by verify and webhook
# ==================================================================

def activate_subscription(user, plan, amount, reference):
    """
    Create or extend a subscription for the user.

    If the user already has an active subscription for the same plan,
    extend the expiry instead of creating a new row.
    """
    today = timezone.localdate()
    days = plan.duration_days

    # Look for an existing active subscription for the same plan
    existing = (
        Subscription.objects
        .filter(
            user=user,
            plan=plan,
            status=Subscription.STATUS_ACTIVE,
            expiry_date__gte=today,
        )
        .order_by('-expiry_date')
        .first()
    )

    if existing:
        existing.expiry_date = existing.expiry_date + timedelta(days=days)
        existing.amount_paid = existing.amount_paid + amount
        existing.payment_reference = reference
        existing.save()
        return existing

    return Subscription.objects.create(
        user=user,
        plan=plan,
        amount_paid=amount,
        currency=plan.currency,
        start_date=today,
        expiry_date=today + timedelta(days=days),
        status=Subscription.STATUS_ACTIVE,
        payment_reference=reference,
    )


# ==================================================================
# 4. WEBHOOK — Paystack calls this directly
# ==================================================================

@csrf_exempt
def paystack_webhook(request):
    """
    Paystack calls this URL on every successful payment.
    This is the authoritative signal — never trust the frontend redirect alone.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    # --- Verify the signature ---
    secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
    signature = request.headers.get('x-paystack-signature', '')
    body = request.body

    expected = hmac.new(secret, body, hashlib.sha512).hexdigest()

    if not hmac.compare_digest(expected, signature):
        logger.warning('Paystack webhook signature mismatch.')
        return HttpResponse(status=401)

    # --- Parse event ---
    try:
        event = json.loads(body.decode('utf-8'))
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    if event.get('event') != 'charge.success':
        return JsonResponse({'status': 'ignored'})

    data = event.get('data', {})
    reference = data.get('reference')

    if not reference:
        return JsonResponse({'status': 'no-reference'})

    # --- Idempotency: already processed? ---
    try:
        payment = Payment.objects.get(reference=reference)
    except Payment.DoesNotExist:
        logger.warning('Webhook for unknown reference: %s', reference)
        return JsonResponse({'status': 'unknown-reference'})

    if payment.status == Payment.STATUS_SUCCESS:
        return JsonResponse({'status': 'already-processed'})

    # --- Verify amounts ---
    amount_ok = int(data.get('amount', 0)) == int(payment.amount * 100)
    if not amount_ok:
        logger.warning('Webhook amount mismatch for %s', reference)
        return JsonResponse({'status': 'amount-mismatch'})

    # --- Activate ---
    payment.status = Payment.STATUS_SUCCESS
    payment.paid_at = timezone.now()
    payment.raw_response = json.dumps(data)
    payment.save()

    subscription = activate_subscription(
        user=payment.user,
        plan=payment.plan,
        amount=payment.amount,
        reference=reference,
    )
    payment.subscription = subscription
    payment.save()

    return JsonResponse({'status': 'ok'})