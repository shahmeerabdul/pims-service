import pytest
from django.core import mail
from django.utils import timezone
from freezegun import freeze_time

from emails.booster_schedule import (
    get_active_writing_day,
    get_due_phase_invite,
    get_enrollment_day,
)
from emails.booster_tasks import (
    send_booster_daily_nudges,
    send_booster_phase_invites,
    send_daily_nudge_email_task,
    send_phase_complete_email_task,
    send_phase_invite_email_task,
)
from emails.builder import build_daily_nudge_email, build_phase_invite_email


def test_build_daily_nudge_email_is_bilingual():
    content = build_daily_nudge_email('Sara', phase=1, day_in_phase=3)

    assert 'Day 3 of Phase 1' in content['subject']
    assert 'مرحلہ 1 کا دن 3' in content['subject']
    assert 'Start today\'s exercise' in content['html_content']
    assert 'آج کی مشق شروع کریں' in content['html_content']
    assert '/dashboard' in content['html_content']


def test_build_phase_invite_email_phase_3():
    content = build_phase_invite_email('Sara', 'phase_3')
    assert 'Your next phase starts soon' in content['subject']
    assert 'updated personal wellbeing summary' in content['html_content']


@pytest.mark.django_db
def test_enrollment_day_and_invite_schedule(test_user):
    onboarding = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
    test_user.onboarding_completed_at = onboarding
    test_user.has_completed_sociodemographic = True
    test_user.save()

    with freeze_time(onboarding):
        assert get_enrollment_day(test_user) == 0

    day_23 = onboarding + timezone.timedelta(days=23)
    with freeze_time(day_23):
        assert get_enrollment_day(test_user) == 23
        assert get_due_phase_invite(test_user) == 'phase_2'


@pytest.mark.django_db
def test_send_daily_nudge_email_task(test_user):
    test_user.full_name = 'Sara Ahmed'
    test_user.has_completed_sociodemographic = True
    test_user.onboarding_completed_at = timezone.now()
    test_user.save()

    result = send_daily_nudge_email_task(
        test_user.user_id,
        wave='PRE_T1',
        phase=1,
        day_in_phase=2,
    )

    assert result['status'] == 'sent'
    assert len(mail.outbox) == 1
    assert 'Day 2 of Phase 1' in mail.outbox[0].subject

    result_again = send_daily_nudge_email_task(
        test_user.user_id,
        wave='PRE_T1',
        phase=1,
        day_in_phase=2,
    )
    assert result_again['status'] == 'skipped'
    assert result_again['reason'] == 'already_sent_today'


@pytest.mark.django_db
def test_send_phase_invite_email_task(test_user):
    test_user.full_name = 'Sara Ahmed'
    test_user.save()

    result = send_phase_invite_email_task(test_user.user_id, 'phase_2')
    assert result['status'] == 'sent'
    assert 'Your next phase starts soon' in mail.outbox[0].subject

    result_again = send_phase_invite_email_task(test_user.user_id, 'phase_2')
    assert result_again['status'] == 'skipped'


@pytest.mark.django_db
def test_send_phase_complete_email_task(test_user):
    test_user.full_name = 'Sara Ahmed'
    test_user.save()

    result = send_phase_complete_email_task(test_user.user_id, 'phase_1_complete')
    assert result['status'] == 'sent'
    assert 'Phase 1 complete' in mail.outbox[0].subject


@pytest.mark.django_db
def test_send_booster_daily_nudges_batch(test_user, test_group):
    test_group.is_active = True
    test_group.save()
    test_user.group = test_group
    test_user.has_completed_sociodemographic = True
    test_user.onboarding_completed_at = timezone.now()
    test_user.save()

    result = send_booster_daily_nudges()
    assert 'Sent 1 booster daily nudges' in result
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_send_booster_phase_invites_batch(test_user):
    onboarding = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
    test_user.has_completed_sociodemographic = True
    test_user.onboarding_completed_at = onboarding
    test_user.save()

    day_83 = onboarding + timezone.timedelta(days=83)
    with freeze_time(day_83):
        result = send_booster_phase_invites()
        assert 'Sent 1 booster phase invites' in result
        assert 'Your next phase starts soon' in mail.outbox[0].subject


@pytest.mark.django_db
def test_get_active_writing_day_uses_platform_state(test_user, test_group):
    test_group.is_active = True
    test_group.save()
    test_user.group = test_group
    test_user.has_completed_sociodemographic = True
    test_user.onboarding_completed_at = timezone.now()
    test_user.save()

    writing_day = get_active_writing_day(test_user)
    assert writing_day is not None
    assert writing_day.phase_number == 1
    assert 1 <= writing_day.day_in_phase <= 7
