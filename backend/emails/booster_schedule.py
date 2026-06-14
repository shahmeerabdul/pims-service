"""Booster / writing-phase email schedule from Psycheversity participant email doc."""

from dataclasses import dataclass

from django.utils import timezone

# Activity wave → study phase number used in E3 subject/body merge fields.
WAVE_TO_PHASE_NUMBER = {
    'PRE_T1': 1,
    'PRE_T_1M': 2,
    'PRE_T2': 3,
    'PRE_T3': 4,
    'PRE_T4': 5,
}

# Enrollment day offsets (Day 0 = onboarding completion date).
PHASE_INVITE_ENROLLMENT_DAYS = {
    2: 'phase_2',      # E5 — booster 1 invite (Day 23)
    3: 'phase_3',      # E7 — booster 2 invite (Day 83)
    4: 'phase_4',      # E9 — booster 3 invite (Day 173)
    5: 'final',        # E11 — final phase invite (Day 358)
}
PHASE_INVITE_DAY_BY_PHASE = {
    2: 23,
    3: 83,
    4: 173,
    5: 358,
}

MILESTONE_PHASE_COMPLETE = {
    '7_DAYS': 'phase_1_complete',    # E4
    '1_MONTH': 'phase_2_complete',   # E6
    '3_MONTHS': 'phase_3_report',    # E8 (with PDF)
    '6_MONTHS': 'phase_4_report',    # E10 (with PDF)
    '1_YEAR': 'study_complete',      # E12 (with PDF + certificate note)
}


@dataclass(frozen=True)
class ActiveWritingDay:
    wave: str
    phase_number: int
    day_in_phase: int


def get_enrollment_day(user) -> int | None:
    """Days elapsed since onboarding completion (Day 0 = onboarding date)."""
    if not user.onboarding_completed_at:
        return None
    onboarding_date = timezone.localtime(user.onboarding_completed_at).date()
    return (timezone.localdate() - onboarding_date).days


def get_active_writing_day(user) -> ActiveWritingDay | None:
    """Return current booster writing day from platform activity state."""
    if getattr(user, 'is_disqualified', False):
        return None
    if not user.onboarding_completed_at:
        return None

    state = user.current_activity_state
    if state is None:
        return None

    phase_number = WAVE_TO_PHASE_NUMBER.get(state.wave)
    if phase_number is None:
        return None

    return ActiveWritingDay(
        wave=state.wave,
        phase_number=phase_number,
        day_in_phase=state.day_in_block,
    )


def get_due_phase_invite(user) -> str | None:
    """Return invite template key if today is the doc-scheduled invite day."""
    enrollment_day = get_enrollment_day(user)
    if enrollment_day is None:
        return None

    for phase_number, invite_key in PHASE_INVITE_ENROLLMENT_DAYS.items():
        if enrollment_day == PHASE_INVITE_DAY_BY_PHASE[phase_number]:
            return invite_key
    return None
