from django import forms
from django.contrib.auth.models import User

from notifications.models import Profile


class UserForm(forms.ModelForm):
    """Edit basic user info — email and name."""

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'you@example.com',
                'autocomplete': 'email',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'First name',
                'autocomplete': 'given-name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Last name',
                'autocomplete': 'family-name',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('That email is already in use.')
        return email


class ProfileForm(forms.ModelForm):
    """Edit Profile fields — phone + notification toggles."""

    class Meta:
        model = Profile
        fields = ('phone_number', 'email_notifications', 'whatsapp_notifications')
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+2348012345678',
                'autocomplete': 'tel',
            }),
        }

    def clean_phone_number(self):
        phone = (self.cleaned_data.get('phone_number') or '').strip()

        # Empty is fine — phone is optional
        if not phone:
            return ''

        # Very light validation: allow +, digits, spaces, hyphens, parens
        allowed = set('+0123456789 -()')
        if not all(ch in allowed for ch in phone):
            raise forms.ValidationError(
                'Use digits only, optionally starting with + (e.g. +2348012345678).'
            )

        # Strip spaces/hyphens/parens for storage
        cleaned = ''.join(ch for ch in phone if ch.isdigit() or ch == '+')

        if len(cleaned.replace('+', '')) < 7:
            raise forms.ValidationError('Phone number looks too short.')

        return cleaned