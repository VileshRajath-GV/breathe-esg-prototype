from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter

from tenants.views import TenantViewSet
from emissions.views import FacilityLookupViewSet, NormalizedRecordViewSet, DashboardSummaryView
from ingestion.views import FileIngestionView

def health(request):
    return JsonResponse({"status": "ok"})

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'facilities', FacilityLookupViewSet, basename='facility')
router.register(r'records', NormalizedRecordViewSet, basename='record')

urlpatterns = [
    path("health/", health),
    path("api/ingest/", FileIngestionView.as_view(), name='file-ingest'),
    path("api/dashboard/summary/", DashboardSummaryView.as_view(), name='dashboard-summary'),
    path("api/", include(router.urls)),
]
