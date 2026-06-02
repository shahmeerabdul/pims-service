from rest_framework.permissions import BasePermission


class OnboardingCompleted(BasePermission):
    """
    Blocks access to experiment endpoints until the user has completed
    the mandatory onboarding (Sociodemographic form).
    """
    message = "You must complete the onboarding assessment before accessing this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_completed_sociodemographic
        )
