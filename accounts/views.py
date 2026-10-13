from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from betting.models import BetCode
from notifications.models import EmailVerification
from notifications.services import send_verification_email
from subscriptions.models import get_active_subscription

from .forms import RegisterForm
from notifications.models import Profile
from .profile_forms import UserForm, ProfileForm


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False   # must verify email first
            user.save()

            sent = send_verification_email(user, request=request)
            if sent:
                messages.success(
                    request,
                    f'Welcome, {user.username}. We sent a confirmation link to {user.email}.',
                )
            else:
                messages.warning(
                    request,
                    f'Account created, but the verification email failed. '
                    f'Please contact {settings.SITE_SUPPORT_EMAIL}.',
                )
            return redirect('accounts:verify_sent')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def verify_sent(request):
    return render(request, 'accounts/verify_sent.html')


def verify_email(request, token):
    try:
        verification = EmailVerification.objects.select_related('user').get(token=token)
    except EmailVerification.DoesNotExist:
        return render(request, 'accounts/verify_email.html', {'status': 'invalid'})

    if verification.is_verified:
        return render(request, 'accounts/verify_email.html', {'status': 'already', 'user': verification.user})

    if verification.is_expired:
        return render(request, 'accounts/verify_email.html', {'status': 'expired', 'user': verification.user})

    verification.verified_at = timezone.now()
    verification.save()

    user = verification.user
    user.is_active = True
    user.save()

    profile = getattr(user, 'profile', None)
    if profile:
        profile.email_verified = True
        profile.save()

    return render(request, 'accounts/verify_email.html', {'status': 'verified', 'user': user})


@login_required
def dashboard(request):
    today = timezone.localdate()
    subscription = get_active_subscription(request.user)

    todays_pick = BetCode.objects.filter(is_published=True, pick_date=today).first()
    if not todays_pick:
        todays_pick = BetCode.objects.filter(is_published=True).order_by('-pick_date', '-created_at').first()

    unlocked_code = None
    if subscription and subscription.is_valid and todays_pick:
        unlocked_code = todays_pick.code

    return render(request, 'accounts/dashboard.html', {
        'subscription': subscription,
        'todays_pick': todays_pick,
        'unlocked_code': unlocked_code,
    })
@login_required
def profile(request):
    """User profile / settings page."""
    user = request.user

    # Make sure a Profile exists (should already — auto-created)
    profile_obj, _ = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, instance=profile_obj)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('accounts:profile')
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile_obj)

    subscription = get_active_subscription(user)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'subscription': subscription,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def delete_account(request):
    """Permanently delete the user's account."""
    if request.method == 'POST':
        user = request.user
        username = user.username
        user.delete()
        messages.success(
            request,
            f'Your account ({username}) has been deleted. '
            f'We\'re sorry to see you go.'
        )
        return redirect('core:home')

    return render(request, 'accounts/delete_account.html')