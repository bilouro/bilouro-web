from django.conf import settings


def site_globals(request):
    return {
        "GISCUS_REPO_ID": settings.GISCUS_REPO_ID,
        "GISCUS_CATEGORY_ID": settings.GISCUS_CATEGORY_ID,
        "PLAUSIBLE_DOMAIN": settings.PLAUSIBLE_DOMAIN,
        "PLAUSIBLE_SCRIPT": settings.PLAUSIBLE_SCRIPT,
        "STUDIO_BOOKING_URL": settings.STUDIO_BOOKING_URL,
    }
