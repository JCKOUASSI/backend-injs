from django.conf import settings


def public_urls(request):
    return {
        'PUBLIC_APP_URL': getattr(settings, 'PUBLIC_APP_URL', 'https://app.sygepcfae.org'),
    }
