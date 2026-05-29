from datetime import datetime, timedelta
from django.db.models import Sum, Avg
from django.db.models.functions import TruncMonth
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response

from emissions.models import FacilityLookup, NormalizedRecord
from emissions.serializers import FacilityLookupSerializer, NormalizedRecordSerializer
from reviews.models import AuditTrail

class FacilityLookupViewSet(viewsets.ModelViewSet):
    queryset = FacilityLookup.objects.all()
    serializer_class = FacilityLookupSerializer

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            return self.queryset.filter(tenant_id=tenant_id)
        return self.queryset

class NormalizedRecordViewSet(viewsets.ModelViewSet):
    queryset = NormalizedRecord.objects.all()
    serializer_class = NormalizedRecordSerializer

    def get_queryset(self):
        queryset = self.queryset
        tenant_id = self.request.query_params.get('tenant_id')
        status_filter = self.request.query_params.get('status')
        
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        
        if status_filter and status_filter != 'all':
            if status_filter == 'review':
                queryset = queryset.filter(status='review')
            elif status_filter == 'error':
                queryset = queryset.filter(status='error')
            elif status_filter == 'validated':
                queryset = queryset.filter(status='validated')
        
        return queryset

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        record = self.get_object()
        if record.is_locked:
            return Response({"error": "Record is already approved and locked."}, status=status.HTTP_400_BAD_REQUEST)
        
        old_values = {
            "status": record.status,
            "is_locked": record.is_locked
        }

        # Approve and Lock
        record.status = 'validated'
        record.is_locked = True
        record.save()

        new_values = {
            "status": record.status,
            "is_locked": record.is_locked
        }

        # Log audit trail
        AuditTrail.objects.create(
            tenant=record.tenant,
            record=record,
            action='approve',
            performed_by=request.data.get('performed_by', 'Sustainability Analyst'),
            old_values=old_values,
            new_values=new_values,
            comment=request.data.get('comment', 'Approved and locked for audit.')
        )

        return Response(NormalizedRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        record = self.get_object()
        if record.is_locked:
            return Response({"error": "Cannot flag a locked record."}, status=status.HTTP_400_BAD_REQUEST)
        
        new_status = request.data.get('status', 'review')
        if new_status not in ['review', 'error']:
            return Response({"error": "Invalid status for flagging. Must be 'review' or 'error'."}, status=status.HTTP_400_BAD_REQUEST)

        old_values = {
            "status": record.status,
            "validation_notes": record.validation_notes
        }

        record.status = new_status
        comment = request.data.get('comment', 'Flagged by analyst.')
        record.validation_notes = f"{record.validation_notes}; [Flagged]: {comment}"
        record.save()

        new_values = {
            "status": record.status,
            "validation_notes": record.validation_notes
        }

        # Log audit trail
        AuditTrail.objects.create(
            tenant=record.tenant,
            record=record,
            action='flag',
            performed_by=request.data.get('performed_by', 'Sustainability Analyst'),
            old_values=old_values,
            new_values=new_values,
            comment=comment
        )

        return Response(NormalizedRecordSerializer(record).data)


class DashboardSummaryView(views.APIView):
    def get(self, request, format=None):
        tenant_id = self.request.query_params.get('tenant_id')
        if not tenant_id:
            return Response({"error": "Missing tenant_id"}, status=status.HTTP_400_BAD_REQUEST)
            
        records = NormalizedRecord.objects.filter(tenant_id=tenant_id)
        
        total_records = records.count()
        scope1_sum = records.filter(scope='Scope 1').aggregate(Sum('normalized_value_tco2e'))['normalized_value_tco2e__sum'] or 0
        scope2_sum = records.filter(scope='Scope 2').aggregate(Sum('normalized_value_tco2e'))['normalized_value_tco2e__sum'] or 0
        scope3_sum = records.filter(scope='Scope 3').aggregate(Sum('normalized_value_tco2e'))['normalized_value_tco2e__sum'] or 0
        avg_confidence = records.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0
        
        # Calculate monthly trends
        today = datetime.today().date()
        one_year_ago = today - timedelta(days=365)
        
        trend_records = records.filter(transaction_date__gte=one_year_ago)
        monthly_trend = trend_records.annotate(month=TruncMonth('transaction_date')).values('month').annotate(total=Sum('normalized_value_tco2e')).order_by('month')
        
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
