import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def send_notification(self, notification_id):
    """Send a pending notification asynchronously and mark it as sent or failed."""
    from notifications.models import Notification

    try:
        notification = Notification.objects.get(pk=notification_id)
        logger.info(
            "Sending %s notification (id=%s) to user %s",
            notification.n_type,
            notification_id,
            notification.user_id,
        )
        notification.status = 'sent'
        notification.save(update_fields=['status'])
        return {'status': 'sent', 'notification_id': notification_id}
    except Notification.DoesNotExist:
        logger.error("Notification id=%s not found", notification_id)
        raise
    except Exception as exc:
        logger.error("Failed to send notification id=%s: %s", notification_id, exc)
        Notification.objects.filter(pk=notification_id).update(status='failed')
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@shared_task
def check_and_send_daily_reminders(reminder_type='morning'):
    """
    Identifies participants who haven't submitted their daily activity
    and sends them a nudge (email/whatsapp).
    """
    from django.contrib.auth import get_user_model
    from activities.models import Submission
    from notifications.models import Notification
    from django.utils import timezone
    from datetime import datetime

    User = get_user_model()
    
    # Define today's range
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Find active participants who haven't finished baseline yet OR have finished it but haven't submitted today
    # (Actually, users only start daily tasks AFTER baseline)
    participants = User.objects.filter(has_completed_sociodemographic=True, is_active=True)
    
    reminded_count = 0
    for user in participants:
        # Check if user submitted today
        has_submitted = Submission.objects.filter(
            user=user,
            submission_date__gte=today_start
        ).exists()
        
        if not has_submitted:
            msg = "Good morning! Don't forget to complete your daily reflection today."
            if reminder_type == 'evening':
                msg = "Good evening! You haven't completed your daily reflection yet. There's still time!"
            
            # Create a notification record (this could be optimized with bulk_create)
            n = Notification.objects.create(
                user=user,
                n_type='email', # Default to email as requested
                message=msg,
                scheduled_time=timezone.now(),
                status='pending'
            )
            # Trigger the individual sending task
            send_notification.delay(n.id)
            reminded_count += 1
            
    return f"Sent {reminded_count} {reminder_type} reminders."


@shared_task
def send_longitudinal_milestone_reminders():
    """
    Identifies participants who are due for longitudinal milestones
    and dispatches a notification/reminder to them.
    """
    from django.contrib.auth import get_user_model
    from notifications.models import Notification
    from django.core.cache import cache
    from django.utils import timezone

    User = get_user_model()
    # Query chunking for KVM2 memory optimization
    active_participants = User.objects.filter(
        is_active=True, 
        has_completed_sociodemographic=True
    ).iterator(chunk_size=1000)

    reminded_count = 0
    now = timezone.now()
    today_date = now.date()

    for user in active_participants:
        due_milestone = user.get_due_milestone
        
        # We only remind for longitudinal post-baseline milestones
        if due_milestone not in ['7_DAYS', '3_MONTHS', '6_MONTHS', '1_YEAR']:
            continue

        # Prevent double-reminding on the same day for the same milestone
        reminder_sent_key = f"user_{user.user_id}_reminded_{due_milestone}_{today_date}"
        if cache.get(reminder_sent_key):
            continue

        # Map milestone to custom reminder message
        milestone_labels = {
            '7_DAYS': '7-day post-test',
            '3_MONTHS': '3-month follow-up',
            '6_MONTHS': '6-month follow-up',
            '1_YEAR': '1-year follow-up',
        }
        label = milestone_labels.get(due_milestone, 'follow-up')
        msg = f"Hello! Your {label} assessment is now due. Please complete it today!"

        n = Notification.objects.create(
            user=user,
            n_type='email',
            message=msg,
            scheduled_time=now,
            status='pending'
        )
        
        send_notification.delay(n.id)

        # Cache the sent status until end of the day (midnight) to prevent double sending
        tomorrow = (now + timezone.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        timeout = int((tomorrow - now).total_seconds())
        if timeout > 0:
            cache.set(reminder_sent_key, True, timeout=timeout)

        reminded_count += 1

    return f"Sent {reminded_count} longitudinal milestone reminders."
