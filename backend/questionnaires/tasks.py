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


@shared_task
def send_month_3_report_task(response_set_id):
    """
    Generate and email the Month-3 PERMA trajectory report PDF to the participant.
    """
    from questionnaires.models import ResponseSet
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    from django.template.loader import render_to_string
    from django.utils import timezone
    from weasyprint import HTML
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import io
    import base64

    logger.info("Starting Month-3 report generation for ResponseSet %s", response_set_id)
    try:
        response_set = ResponseSet.objects.select_related('user', 'user__group').get(id=response_set_id)
        user = response_set.user
        
        if not user.email:
            logger.error("User %s has no email address configured. Skipping report email.", user.username)
            return {"status": "skipped", "reason": "missing_email"}

        # 1. Fetch completed psychometric response sets for the user
        milestone_order = ['SIGNUP', '7_DAYS', '1_MONTH', '3_MONTHS']
        completed_sets = ResponseSet.objects.filter(
            user=user,
            status='COMPLETED',
            milestone__in=milestone_order,
            questionnaire__assessment_type='PSYCHOMETRIC'
        )

        scores_by_ms = {rs.milestone: rs.scores for rs in completed_sets if rs.scores}
        
        x_labels = []
        subscales = [
            ('PERMA_P', 'P'),
            ('PERMA_E', 'E'),
            ('PERMA_R', 'R'),
            ('PERMA_M', 'M'),
            ('PERMA_A', 'A'),
            ('PERMA_N', 'N'),
            ('PERMA_H', 'H'),
            ('PERMA_LON', 'Lon'),
            ('PERMA_OVERALL', 'Overall')
        ]
        
        y_values = {key: [] for key, _ in subscales}
        
        milestone_mapping = [
            ('SIGNUP', 'T0'),
            ('7_DAYS', 'T1'),
            ('1_MONTH', '1-Month'),
            ('3_MONTHS', 'T2')
        ]
        
        for ms, label in milestone_mapping:
            if ms in scores_by_ms:
                x_labels.append(label)
                for key, _ in subscales:
                    val = scores_by_ms[ms].get(key, 0.0)
                    try:
                        val = float(val)
                    except (TypeError, ValueError):
                        val = 0.0
                    y_values[key].append(val)

        if not x_labels:
            logger.error("No PERMA scores found for user %s. Skipping report email.", user.username)
            return {"status": "skipped", "reason": "no_scores"}

        # 2. Render Matplotlib 3x3 Grid of Line Charts
        fig, axes = plt.subplots(3, 3, figsize=(9, 9), dpi=300)
        fig.subplots_adjust(hspace=0.4, wspace=0.3)
        
        for idx, (key, label) in enumerate(subscales):
            row = idx // 3
            col = idx % 3
            ax = axes[row, col]
            
            ax.plot(
                x_labels, 
                y_values[key], 
                color='#2E4E90', 
                marker='o', 
                markersize=5, 
                linewidth=2.0, 
                markerfacecolor='#C8A951', 
                markeredgecolor='#2E4E90'
            )
            
            ax.set_ylim(0, 10.5)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#2E4E90')
            ax.spines['bottom'].set_color('#2E4E90')
            ax.tick_params(colors='#2E4E90', labelsize=8)
            ax.grid(axis='y', linestyle='--', alpha=0.5, color='#ccc')
            ax.set_title(label, color='#2E4E90', fontweight='bold', fontsize=10, pad=6)
            
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
        plt.close(fig)
        buf.seek(0)
        chart_image_base64 = base64.b64encode(buf.read()).decode('utf-8')

        # Load logo image if exists (try multiple directories and names)
        import os
        logo_base64 = ""
        possible_dirs = [
            os.path.join(settings.BASE_DIR, 'static'),
            settings.BASE_DIR,
            os.path.dirname(settings.BASE_DIR)
        ]
        logo_filenames = ['pims_logo.png', 'pims_logo-removebg.png', 'pims_logo.jpg', 'pims_logo.jpeg']
        found_logo = False
        for directory in possible_dirs:
            for filename in logo_filenames:
                logo_path = os.path.join(directory, filename)
                if os.path.exists(logo_path):
                    try:
                        with open(logo_path, "rb") as f:
                            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
                        found_logo = True
                        logger.info("Found logo at: %s", logo_path)
                        break
                    except Exception as logo_err:
                        logger.warning("Failed to read logo at %s: %s", logo_path, logo_err)
            if found_logo:
                break

        # 3. Render HTML template
        context = {
            'user_id': user.user_id,
            'group_name': user.group.name if user.group else 'N/A',
            'date': timezone.now().strftime('%Y-%m-%d'),
            'chart_image': chart_image_base64,
            'logo_image': logo_base64,
        }
        html_string = render_to_string('questionnaires/month3_report.html', context)

        # 4. Generate PDF via WeasyPrint
        pdf_bytes = HTML(string=html_string).write_pdf()

        # 5. Email PDF Attachment
        subject = "Three Months PERMA Profiler Report / تین ماہ کی PERMA پروفائلر رپورٹ"
        text_content = (
            f"Dear Participant,\n\n"
            f"Please find attached your Month-3 PERMA feedback report. Please continue to your next entries.\n\n"
            f"Sincerely,\n"
            f"PIMS Team\n\n"
            f"--------------------------------------------------\n\n"
            f"محترم شریک کار،\n\n"
            f"براہ کرم منسلک فائل میں اپنے تیسرے مہینے کی PERMA فیڈبیک رپورٹ حاصل کریں۔ براہ کرم اپنے اگلے اندراجات جاری رکھیں۔\n\n"
            f"شکریہ،\n"
            f"PIMS ٹیم"
        )
        
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e4e4e7; border-radius: 8px;">
            <h2 style="color: #2E4E90; margin-top: 0;">PIMS Feedback Report</h2>
            <p style="font-size: 15px; color: #18181b;">Dear Participant,</p>
            <p style="color: #3f3f46; font-size: 15px; line-height: 1.5;">
                Please find attached your Month-3 PERMA feedback report in PDF format. Please continue to your next entries.
            </p>
            <hr style="border: 0; border-top: 1px solid #e4e4e7; margin: 20px 0;">
            <div style="direction: rtl; text-align: right; font-family: Arial, sans-serif;">
                <p style="font-size: 16px; color: #2E4E90; margin-top: 0;">پی آئی ایم ایس فیڈبیک رپورٹ</p>
                <p style="font-size: 15px; color: #18181b;">محترم شریک کار،</p>
                <p style="color: #3f3f46; font-size: 15px; line-height: 1.5;">
                    براہ کرم منسلک فائل میں اپنے تیسرے مہینے کی PERMA فیڈبیک رپورٹ حاصل کریں۔ براہ کرم اپنے اگلے اندراجات جاری رکھیں۔
                </p>
            </div>
            <hr style="border: 0; border-top: 1px solid #e4e4e7; margin: 20px 0;">
            <p style="color: #71717a; font-size: 12px; margin-bottom: 0;">
                This is an automated message from the Pakistan Intervention Management System. Please do not reply directly to this email.
            </p>
        </div>
        """
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_body, "text/html")
        msg.attach("pims_month3_report.pdf", pdf_bytes, "application/pdf")
        msg.send(fail_silently=False)
        
        logger.info("Successfully sent Month-3 report email to user %s (%s)", user.username, user.email)
        return {"status": "sent", "recipient": user.email}
    except Exception as e:
        logger.exception("Failed to generate and send Month-3 report email:")
        return {"status": "error", "error": str(e)}
