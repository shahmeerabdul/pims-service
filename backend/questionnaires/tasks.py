import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def refresh_suicide_risk_admin_cache_task():
    """Daily Celery job: fetch flagged users from DB and store in Redis."""
    from .safety_cache import refresh_suicide_risk_admin_cache

    payload = refresh_suicide_risk_admin_cache()
    logger.info(
        "Suicide risk admin cache refreshed: %s flagged, %s opted in for follow-up.",
        payload["total_flagged"],
        payload["opt_in_count"],
    )
    return {
        "total_flagged": payload["total_flagged"],
        "opt_in_count": payload["opt_in_count"],
        "last_refreshed_at": payload["last_refreshed_at"],
    }
