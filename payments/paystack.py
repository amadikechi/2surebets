"""
Thin wrapper around the Paystack API.

Docs: https://paystack.com/docs/api/
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PaystackError(Exception):
    """Any error thrown by the Paystack integration."""


def _headers():
    return {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }


def _url(path):
    return f'{settings.PAYSTACK_BASE_URL}{path}'


def initialize_transaction(email, amount_kobo, reference, callback_url, metadata=None):
    """
    Create a Paystack transaction. Returns the authorization_url
    the user should be redirected to.

    amount_kobo: amount in the smallest currency unit (kobo for NGN).
    """
    payload = {
        'email': email,
        'amount': amount_kobo,
        'reference': reference,
        'callback_url': callback_url,
        'currency': settings.PAYSTACK_CURRENCY,
    }
    if metadata:
        payload['metadata'] = metadata

    try:
        response = requests.post(
            _url('/transaction/initialize'),
            json=payload,
            headers=_headers(),
            timeout=15,
        )
    except requests.RequestException as exc:
        logger.exception('Paystack initialize request failed')
        raise PaystackError(f'Could not reach Paystack: {exc}') from exc

    data = response.json()
    if not response.ok or not data.get('status'):
        message = data.get('message', 'Unknown error')
        logger.error('Paystack initialize failed: %s', data)
        raise PaystackError(f'Paystack error: {message}')

    return data['data']['authorization_url']


def verify_transaction(reference):
    """
    Verify a transaction by reference. Returns the `data` dict on success.
    Raises PaystackError on failure.
    """
    try:
        response = requests.get(
            _url(f'/transaction/verify/{reference}'),
            headers=_headers(),
            timeout=15,
        )
    except requests.RequestException as exc:
        logger.exception('Paystack verify request failed')
        raise PaystackError(f'Could not reach Paystack: {exc}') from exc

    data = response.json()
    if not response.ok or not data.get('status'):
        message = data.get('message', 'Unknown error')
        logger.error('Paystack verify failed: %s', data)
        raise PaystackError(f'Paystack error: {message}')

    return data['data']