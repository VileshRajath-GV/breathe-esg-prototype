from datetime import datetime, timedelta
from django.db.models import Sum, Avg
from django.db.models.functions import TruncMonth
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response

from emissions.models import FacilityProfile, NormalisedEmissionRecord
from emissions.serializers import (
    FacilityProfileSerializer,
    NormalisedEmissionRecordSerializer,
    # Backwards-compatible aliases kept for any external import
    FacilityLookupSerializer,
    NormalizedRecordSerializer,
)
from reviews.models import AuditEntry

class FacilityLookupViewSet(viewsets.ModelViewSet):
    """Viewset for FacilityProfile — name kept for URL router backwards-compat."""
    queryset = FacilityProfile.objects.all()
    serializer_class = FacilityProfileSerializer

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            return self.queryset.filter(tenant_id=tenant_id)
        return self.queryset

class NormalizedRecordViewSet(viewsets.ModelViewSet):
    """Viewset for NormalisedEmissionRecord — name kept for URL router backwards-compat."""
    queryset = NormalisedEmissionRecord.objects.all()
    serializer_class = NormalisedEmissionRecordSerializer

    def get_queryset(self):
        queryset = self.queryset
        tenant_id = self.request.query_params.get('tenant_id')
        status_filter = self.request.query_params.get('status')

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        if status_filter and status_filter != 'all':
            status_map = {
                'review': 'NEEDS_REVIEW',
                'error':  'NEEDS_REVIEW',
                'validated': 'APPROVED',
            }
            mapped = status_map.get(status_filter)
            if mapped:
                queryset = queryset.filter(review_status=mapped)

        return queryset

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        record = self.get_object()
        from emissions.choices import ReviewStatus
        if record.review_status == ReviewStatus.LOCKED:
            return Response({"error": "Record is already locked for audit."}, status=status.HTTP_400_BAD_REQUEST)

        old_status = record.review_status
        record.review_status = ReviewStatus.APPROVED
        record.save()

        AuditEntry.objects.create(
            tenant=record.tenant,
            object_type="NormalisedEmissionRecord",
            object_id=record.id,
            action=AuditEntry.ACTION_STATUS_CHANGE,
            field_name="review_status",
            before_value=old_status,
            after_value=record.review_status,
            note=request.data.get('comment', 'Approved by analyst.')
        )

        return Response(NormalisedEmissionRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        record = self.get_object()
        from emissions.choices import ReviewStatus
        if record.review_status == ReviewStatus.LOCKED:
            return Response({"error": "Cannot flag a locked record."}, status=status.HTTP_400_BAD_REQUEST)

        old_status = record.review_status
        record.review_status = ReviewStatus.NEEDS_REVIEW
        comment = request.data.get('comment', 'Flagged by analyst.')
        record.review_notes = f"{record.review_notes}; [Flagged]: {comment}".strip('; ')
        record.anomaly_flag = True
        record.anomaly_reason = comment
        record.save()

        AuditEntry.objects.create(
            tenant=record.tenant,
            object_type="NormalisedEmissionRecord",
            object_id=record.id,
            action=AuditEntry.ACTION_STATUS_CHANGE,
            field_name="review_status",
            before_value=old_status,
            after_value=record.review_status,
            note=comment
        )

        return Response(NormalisedEmissionRecordSerializer(record).data)


class DashboardSummaryView(views.APIView):
    def get(self, request, format=None):
        tenant_id = self.request.query_params.get('tenant_id')
        if not tenant_id:
            return Response({"error": "Missing tenant_id"}, status=status.HTTP_400_BAD_REQUEST)

        records = NormalisedEmissionRecord.objects.filter(tenant_id=tenant_id)
        
        total_records = records.count()
        scope1_sum = records.filter(scope='SCOPE_1').aggregate(Sum('co2e_kg'))['co2e_kg__sum'] or 0
        scope2_sum = records.filter(scope='SCOPE_2').aggregate(Sum('co2e_kg'))['co2e_kg__sum'] or 0
        scope3_sum = records.filter(scope='SCOPE_3').aggregate(Sum('co2e_kg'))['co2e_kg__sum'] or 0
        avg_confidence = records.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0

        # Calculate monthly trends
        today = datetime.today().date()
        one_year_ago = today - timedelta(days=365)

        trend_records = records.filter(period_start__gte=one_year_ago)
        monthly_trend = (
            trend_records
            .annotate(month=TruncMonth('period_start'))
            .values('month')
            .annotate(total=Sum('co2e_kg'))
            .order_by('month')
        )
        trend_data = []
        months_dict = {}
        for m in monthly_trend:
            if m['month']:
                month_key = m['month'].strftime('%Y-%m')
                months_dict[month_key] = float(m['total'])
                
        # Generate last 12 months starting from 11 months ago
        current = today - timedelta(days=335)
        for i in range(12):
            month_key = current.strftime('%Y-%m')
            month_name = current.strftime('%b')
            total = months_dict.get(month_key, 0.0)
            trend_data.append({
                "label": month_name,
                "value": round(total, 2)
            })
            
            # Move to next month
            if current.month == 12:
                current = datetime(current.year + 1, 1, 1).date()
            else:
                try:
                    current = datetime(current.year, current.month + 1, 1).date()
                except ValueError:
                    current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
                
        total_sum = float(scope1_sum + scope2_sum + scope3_sum)
        if total_sum > 0:
            scope1_pct = round((float(scope1_sum) / total_sum) * 100, 1)
            scope2_pct = round((float(scope2_sum) / total_sum) * 100, 1)
            scope3_pct = round((float(scope3_sum) / total_sum) * 100, 1)
        else:
            scope1_pct, scope2_pct, scope3_pct = 0.0, 0.0, 0.0
            
        return Response({
            "total_records": total_records,
            "scope1_emissions": round(float(scope1_sum), 2),
            "scope2_emissions": round(float(scope2_sum), 2),
            "scope3_emissions": round(float(scope3_sum), 2),
            "data_quality": round(float(avg_confidence), 1),
            "trend": trend_data,
            "scopes": {
                "scope1": scope1_pct,
                "scope2": scope2_pct,
                "scope3": scope3_pct
            }
        })
