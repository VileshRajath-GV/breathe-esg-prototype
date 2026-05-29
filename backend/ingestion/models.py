import uuid
from django.db import models
from tenants.models import Tenant

class UploadBatch(models.Model):
    SOURCE_TYPES = [
        ('SAP', 'SAP ERP Export'),
        ('Utility', 'Utility Portal Export'),
        ('Travel', 'Corporate Travel API/JSON'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='upload_batches')
    filename = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    row_count = models.IntegerField(default=0)
    error_summary = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.source_type} Batch - {self.filename} ({self.status})"

class RawIngestedData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(UploadBatch, on_delete=models.CASCADE, related_name='raw_rows')
    row_index = models.IntegerField()
    raw_payload = models.JSONField(help_text="Stores the exact raw source row for audit and reproducibility.")

    class Meta:
        ordering = ['row_index']

    def __str__(self):
        return f"Raw Row {self.row_index} in batch {self.batch.id}"
