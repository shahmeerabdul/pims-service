from rest_framework import generics, permissions
from .models import Phase
from .serializers import PhaseSerializer
from django.utils import timezone
from users.permissions import OnboardingCompleted

class PhaseListView(generics.ListAPIView):
    queryset = Phase.objects.all()
    serializer_class = PhaseSerializer
    permission_classes = (permissions.IsAuthenticated, OnboardingCompleted,)

class CurrentPhaseView(generics.RetrieveAPIView):
    serializer_class = PhaseSerializer
    permission_classes = (permissions.IsAuthenticated, OnboardingCompleted,)

    def get_object(self):
        today = timezone.localdate()
        return Phase.objects.filter(start_date__lte=today, end_date__gte=today).first()
