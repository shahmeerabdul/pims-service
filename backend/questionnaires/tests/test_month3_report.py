import pytest
from django.core import mail
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from users.models import User, Role
from questionnaires.models import Questionnaire, Question, Option, ResponseSet, Response
from questionnaires.tasks import send_month_3_report_task
from questionnaires.serializers import ResponseSetSubmitSerializer

@pytest.fixture
def participant_role(db):
    return Role.objects.get_or_create(name='Participant')[0]

@pytest.fixture
def user(db, participant_role):
    return User.objects.create_user(
        username='test_participant',
        email='participant@test.com',
        password='password123',
        role=participant_role,
        has_completed_sociodemographic=True,
        onboarding_completed_at=timezone.now() - timedelta(days=90)
    )

@pytest.fixture
def psych_questionnaire(db):
    q = Questionnaire.objects.create(
        title='Psychometric Battery',
        assessment_type='PSYCHOMETRIC',
        is_active=True
    )
    # Create a dummy question
    Question.objects.create(questionnaire=q, content='PERMA Q1', type='SCALE', order=1)
    return q

@pytest.mark.django_db(transaction=True)
class TestMonth3Report:

    def test_report_generation_and_email(self, user, psych_questionnaire):
        # 1. Create completed response sets with scores for SIGNUP, 7_DAYS, 1_MONTH
        rs_signup = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='COMPLETED',
            milestone='SIGNUP',
            scores={
                'PERMA_P': 6.0, 'PERMA_E': 6.2, 'PERMA_R': 5.8, 'PERMA_M': 6.5,
                'PERMA_A': 6.1, 'PERMA_N': 4.0, 'PERMA_H': 7.0, 'PERMA_LON': 3.5,
                'PERMA_OVERALL': 6.5
            },
            completed_at=timezone.now() - timedelta(days=90)
        )
        rs_7days = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='COMPLETED',
            milestone='7_DAYS',
            scores={
                'PERMA_P': 6.8, 'PERMA_E': 7.0, 'PERMA_R': 6.5, 'PERMA_M': 7.2,
                'PERMA_A': 6.9, 'PERMA_N': 3.5, 'PERMA_H': 7.5, 'PERMA_LON': 3.0,
                'PERMA_OVERALL': 7.2
            },
            completed_at=timezone.now() - timedelta(days=83)
        )
        rs_1month = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='COMPLETED',
            milestone='1_MONTH',
            scores={
                'PERMA_P': 7.5, 'PERMA_E': 7.6, 'PERMA_R': 7.2, 'PERMA_M': 7.8,
                'PERMA_A': 7.5, 'PERMA_N': 3.0, 'PERMA_H': 8.0, 'PERMA_LON': 2.5,
                'PERMA_OVERALL': 7.8
            },
            completed_at=timezone.now() - timedelta(days=60)
        )
        rs_3months = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='COMPLETED',
            milestone='3_MONTHS',
            scores={
                'PERMA_P': 8.2, 'PERMA_E': 8.4, 'PERMA_R': 8.0, 'PERMA_M': 8.5,
                'PERMA_A': 8.3, 'PERMA_N': 2.5, 'PERMA_H': 8.5, 'PERMA_LON': 2.0,
                'PERMA_OVERALL': 8.5
            },
            completed_at=timezone.now()
        )

        # 2. Run the task synchronously
        res = send_month_3_report_task(rs_3months.id)
        
        assert res['status'] == 'sent'
        assert res['recipient'] == 'participant@test.com'

        # 3. Assert email is in outbox
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ['participant@test.com']
        assert "Phase complete" in email.subject
        assert "wellbeing summary" in email.subject
        assert "You have completed this phase" in email.body
        assert "PERMA Profiler" in email.body
        assert "following phase will begin" in email.body
        assert "آپ نے یہ مرحلہ مکمل کر لیا ہے" in email.body

        # 4. Assert PDF attachment is present
        assert len(email.attachments) == 1
        attachment_name, attachment_data, mime_type = email.attachments[0]
        assert attachment_name == "pims_month3_report.pdf"
        assert mime_type == "application/pdf"
        assert len(attachment_data) > 0  # Assert it's non-empty PDF bytes

    @patch('questionnaires.tasks.send_month_3_report_task.delay')
    def test_submission_triggers_month3_report_task(self, mock_delay, user, psych_questionnaire):
        # Create a draft response set for 3_MONTHS
        rs = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='DRAFT',
            milestone='3_MONTHS'
        )

        # Submit it using ResponseSetSubmitSerializer
        data = {
            'responses_data': []
        }
        
        serializer = ResponseSetSubmitSerializer(instance=rs, data=data)
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        # Check that the celery delay task was triggered
        mock_delay.assert_called_once_with(rs.id)

    def test_report_generation_with_missing_milestones(self, user, psych_questionnaire):
        # Only SIGNUP and 3_MONTHS completed (7_DAYS and 1_MONTH are missing)
        rs_signup = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='COMPLETED',
            milestone='SIGNUP',
            scores={
                'PERMA_P': 6.0, 'PERMA_E': 6.2, 'PERMA_R': 5.8, 'PERMA_M': 6.5,
                'PERMA_A': 6.1, 'PERMA_N': 4.0, 'PERMA_H': 7.0, 'PERMA_LON': 3.5,
                'PERMA_OVERALL': 6.5
            },
            completed_at=timezone.now() - timedelta(days=90)
        )
        rs_3months = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='COMPLETED',
            milestone='3_MONTHS',
            scores={
                'PERMA_P': 8.2, 'PERMA_E': 8.4, 'PERMA_R': 8.0, 'PERMA_M': 8.5,
                'PERMA_A': 8.3, 'PERMA_N': 2.5, 'PERMA_H': 8.5, 'PERMA_LON': 2.0,
                'PERMA_OVERALL': 8.5
            },
            completed_at=timezone.now()
        )

        mail.outbox.clear()
        res = send_month_3_report_task(rs_3months.id)
        assert res['status'] == 'sent'
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert len(email.attachments) == 1
        assert email.attachments[0][0] == "pims_month3_report.pdf"

    def test_report_generation_with_malformed_scores(self, user, psych_questionnaire):
        # Signup has invalid score formats (strings or None)
        rs_signup = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='COMPLETED',
            milestone='SIGNUP',
            scores={
                'PERMA_P': 'invalid_string', 'PERMA_E': 6.2, 'PERMA_R': 5.8, 'PERMA_M': None,
                'PERMA_A': 6.1, 'PERMA_N': 4.0, 'PERMA_H': 7.0, 'PERMA_LON': 3.5,
                'PERMA_OVERALL': 6.5
            },
            completed_at=timezone.now() - timedelta(days=90)
        )
        rs_3months = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='COMPLETED',
            milestone='3_MONTHS',
            scores={
                'PERMA_P': 8.2, 'PERMA_E': 8.4, 'PERMA_R': 8.0, 'PERMA_M': 8.5,
                'PERMA_A': 8.3, 'PERMA_N': 2.5, 'PERMA_H': 8.5, 'PERMA_LON': 2.0,
                'PERMA_OVERALL': 8.5
            },
            completed_at=timezone.now()
        )

        mail.outbox.clear()
        res = send_month_3_report_task(rs_3months.id)
        assert res['status'] == 'sent'
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert len(email.attachments) == 1

    def test_report_generation_skipped_if_no_scores(self, user, psych_questionnaire):
        # User has completed sets but scores is empty dict
        rs_signup = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='COMPLETED',
            milestone='SIGNUP',
            scores={},
            completed_at=timezone.now() - timedelta(days=90)
        )
        rs_3months = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='COMPLETED',
            milestone='3_MONTHS',
            scores={},
            completed_at=timezone.now()
        )

        mail.outbox.clear()
        res = send_month_3_report_task(rs_3months.id)
        assert res['status'] == 'skipped'
        assert res['reason'] == 'no_scores'
        assert len(mail.outbox) == 0

    def test_report_generation_skipped_if_no_email(self, user, psych_questionnaire):
        # Set user email to empty string
        user.email = ""
        user.save()

        rs_3months = ResponseSet.objects.create(
            user=user,
            questionnaire=psych_questionnaire,
            status='COMPLETED',
            milestone='3_MONTHS',
            scores={'PERMA_OVERALL': 8.5},
            completed_at=timezone.now()
        )

        mail.outbox.clear()
        res = send_month_3_report_task(rs_3months.id)
        assert res['status'] == 'skipped'
        assert res['reason'] == 'missing_email'
        assert len(mail.outbox) == 0
