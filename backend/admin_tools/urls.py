from django.urls import path
from .views import (
    ExportDataCSVView, 
    AdminDashboardAnalyticsView, 
    ExportT0DataCSVView,
    ExportLongitudinalDataCSVView,
    ExportTaskStatusView
)

urlpatterns = [
    path('export/csv/', ExportDataCSVView.as_view(), name='export_csv'),
    path('export/t0/csv/', ExportT0DataCSVView.as_view(), name='export_t0_csv'),
    path('export/longitudinal/csv/', ExportLongitudinalDataCSVView.as_view(), name='export_longitudinal_csv'),
    path('export/status/<uuid:task_id>/', ExportTaskStatusView.as_view(), name='export_task_status'),
    path('dashboard-analytics/', AdminDashboardAnalyticsView.as_view(), name='dashboard_analytics'),
]
