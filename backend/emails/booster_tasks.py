import logging

from celery import shared_task
from celery.exceptions import Retry
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from .booster_schedule import (
    get_active_writing_day,
    get_due_phase_invite,
)
from .builder import (
    build_daily_nudge_email,
    build_phase_complete_email,
    build_phase_invite_email,
    get_first_name,
)
from .tasks import _send_participant_email

logger = logging.getLogger(__name__)
User = get_user_model()


def _booster_e3_cache_key(user_id: int, wave: str, day_in_phase: int) -> str:
    today = timezone.localdate().isoformat()
    return f'booster_e3_{user_id}_{wave}_{day_in_phase}_{today}'


def _booster_invite_cache_key(user_id: int, invite_key: str) -> str:
    return f'booster_invite_{user_id}_{invite_key}'


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_daily_nudge_email_task(self, user_id: int, *, wave: str, phase: int, day_in_phase: int):
    """Send E3 bilingual daily writing nudge for an active booster day."""
    cache_key = _booster_e3_cache_key(user_id, wave, day_in_phase)
    if cache.get(cache_key):
        return {'status': 'skipped', 'reason': 'already_sent_today'}

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return {'status': 'skipped', 'reason': 'user_not_found'}

    if not user.email or user.is_disqualified or not user.is_active:
        return {'status': 'skipped', 'reason': 'ineligible'}

    first_name = get_first_name(user)
    email_content = build_daily_nudge_email(
        first_name,
        phase=phase,
        day_in_phase=day_in_phase,
    )

    try:
        _send_participant_email(email_content, user.email)
        cache.set(cache_key, True, timeout=86400)
        logger.info(
            'Sent daily nudge (phase %s day %s) to %s',
            phase, day_in_phase, user.email,
        )
        return {'status': 'sent', 'recipient': user.email}
    except Exception as exc:
        logger.error('Error sending daily nudge to %s: %s', user.email, exc)
        if isinstance(exc, Retry):
            raise
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_phase_invite_email_task(self, user_id: int, invite_key: str):
    """Send E5/E7/E9/E11 bilingual phase invite before a booster window."""
    cache_key = _booster_invite_cache_key(user_id, invite_key)
    if cache.get(cache_key):
        return {'status': 'skipped', 'reason': 'already_sent'}

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return {'status': 'skipped', 'reason': 'user_not_found'}

    if not user.email or user.is_disqualified or not user.is_active:
        return {'status': 'skipped', 'reason': 'ineligible'}

    first_name = get_first_name(user)
    email_content = build_phase_invite_email(first_name, invite_key)

    try:
        _send_participant_email(email_content, user.email)
        cache.set(cache_key, True, timeout=86400 * 400)
        logger.info('Sent phase invite (%s) to %s', invite_key, user.email)
        return {'status': 'sent', 'recipient': user.email}
    except Exception as exc:
        logger.error('Error sending phase invite to %s: %s', user.email, exc)
        if isinstance(exc, Retry):
            raise
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_phase_complete_email_task(
    self,
    user_id: int,
    template_key: str,
    *,
    attachments: list | None = None,
):
    """Send E4/E6/E8/E10/E12 bilingual phase-complete email."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return {'status': 'skipped', 'reason': 'user_not_found'}

    if not user.email or user.is_disqualified:
        return {'status': 'skipped', 'reason': 'ineligible'}

    first_name = get_first_name(user)
    email_content = build_phase_complete_email(first_name, template_key)
    attachment_tuples = attachments or []

    try:
        _send_participant_email(email_content, user.email, attachments=attachment_tuples)
        logger.info('Sent phase complete email (%s) to %s', template_key, user.email)
        return {'status': 'sent', 'recipient': user.email}
    except Exception as exc:
        logger.error('Error sending phase complete email to %s: %s', user.email, exc)
        if isinstance(exc, Retry):
            raise
        raise self.retry(exc=exc) from exc


@shared_task
def send_booster_daily_nudges():
    """Celery Beat: send E3 to every participant in an active 7-day writing window."""
    participants = User.objects.filter(
        has_completed_sociodemographic=True,
        is_active=True,
        is_disqualified=False,
        onboarding_completed_at__isnull=False,
    )

    sent = 0
    for user in participants.iterator(chunk_size=500):
        writing_day = get_active_writing_day(user)
        if writing_day is None:
            continue

        result = send_daily_nudge_email_task(
            user.user_id,
            wave=writing_day.wave,
            phase=writing_day.phase_number,
            day_in_phase=writing_day.day_in_phase,
        )
        if isinstance(result, dict) and result.get('status') == 'sent':
            sent += 1

    return f'Sent {sent} booster daily nudges.'


@shared_task
def send_booster_phase_invites():
    """Celery Beat: send phase invite emails on doc-scheduled enrollment days."""
    participants = User.objects.filter(
        has_completed_sociodemographic=True,
        is_active=True,
        is_disqualified=False,
        onboarding_completed_at__isnull=False,
    )

    sent = 0
    for user in participants.iterator(chunk_size=500):
        invite_key = get_due_phase_invite(user)
        if invite_key is None:
            continue

        result = send_phase_invite_email_task(user.user_id, invite_key)
        if isinstance(result, dict) and result.get('status') == 'sent':
            sent += 1

    return f'Sent {sent} booster phase invites.'