from django.conf import settings


def site_info(request):
    """
    Makes site-wide branding values available in every template.

    Usage in a template:
        {{ site_name }}
        {{ site_domain }}
        {{ site_tagline }}
    """
    return {
        'site_name': settings.SITE_NAME,
        'site_domain': settings.SITE_DOMAIN,
        'site_tagline': settings.SITE_TAGLINE,
        'site_support_email': settings.SITE_SUPPORT_EMAIL,
    }