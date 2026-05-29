import os
import tempfile
from django.core.files.storage import default_storage
from rest_framework import status, views
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from tenants.models import Tenant
from ingestion.models import UploadBatch
from ingestion.serializers import UploadBatchSerializer
from ingestion.parsers import SAPParser, UtilityParser, TravelParser

class FileIngestionView(views.APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, format=None):
        file_obj = request.FILES.get('file')
        source_type = request.data.get('source_type')
        tenant_id = request.data.get('tenant_id')

        if not file_obj:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        if source_type not in ['SAP', 'Utility', 'Travel']:
            return Response({"error": "Invalid source_type. Must be 'SAP', 'Utility', or 'Travel'."}, status=status.HTTP_400_BAD_REQUEST)

        if not tenant_id:
            return Response({"error": "Missing tenant_id."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({"error": f"Tenant with ID {tenant_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Create UploadBatch
        batch = UploadBatch.objects.create(
            tenant=tenant,
            filename=file_obj.name,
            source_type=source_type,
            status='processing'
        )

        # 2. Save file temporarily
        try:
            suffix = os.path.splitext(file_obj.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                for chunk in file_obj.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            # 3. Parse file based on source type
            rows_processed = 0
            if source_type == 'SAP':
                parser = SAPParser(batch)
                rows_processed = parser.parse(temp_file_path)
            elif source_type == 'Utility':
                parser = UtilityParser(batch)
                rows_processed = parser.parse(temp_file_path)
            elif source_type == 'Travel':
                parser = TravelParser(batch)
                rows_processed = parser.parse_file(temp_file_path)

            # Cleanup temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            # 4. Mark batch completed
            batch.status = 'completed'
            batch.row_count = rows_processed
            batch.save()

            return Response({
                "message": "File uploaded and processed successfully.",
                "batch": UploadBatchSerializer(batch).data,
                "rows_processed": rows_processed
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Mark batch failed
            batch.status = 'failed'
            batch.error_summary = str(e)
            batch.save()
            
            # Try to cleanup temp file if it still exists
            try:
                if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception:
                pass

            return Response({
                "error": "File ingestion failed during processing.",
                "details": str(e),
                "batch_id": batch.id
            }, status=status.HTTP_400_BAD_REQUEST)
