import uuid
from django.db import models
from tenants.models import Tenant
from ingestion.models import UploadBatch, RawIngestedData

class FacilityLookup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='facility_lookups')
    code = models.CharField(max_length=100, help_text="e.g. SAP WERKS plant code '1000' or Utility Meter ID 'MTR-992'")
    facility_name = models.CharField(max_length=255, help_text="e.g. 'Plant A' or 'Office C'")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tenant', 'code')

    def __str__(self):
        return f"{self.tenant.name}: {self.code} -> {self.facility_name}"

class NormalizedRecord(models.Model):
    SCOPE_CHOICES = [
        ('Scope 1', 'Scope 1 - Direct Emissions'),
        ('Scope 2', 'Scope 2 - Indirect Electricity'),
        ('Scope 3', 'Scope 3 - Value Chain / Travel / Procurement'),
    ]

    STATUS_CHOICES = [
        ('validated', 'Validated'),
        ('review', 'Needs Review'),
        ('error', 'Critical Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='records')
    batch = models.ForeignKey(UploadBatch, on_delete=models.CASCADE, related_name='records')
    raw_data = models.ForeignKey(RawIngestedData, on_delete=models.CASCADE, related_name='normalized_records')
    
    facility = models.CharField(max_length=255, help_text="Resolved user-friendly facility name")
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=100, help_text="e.g. Stationary Combustion, Grid Purchased Electricity, Business Travel")
    activity_type = models.CharField(max_length=100, help_text="e.g. Diesel, Grid Electricity, Air Flight, Hotel Stay")
    
    raw_value = models.DecimalField(max_digits=18, decimal_places=4)
    raw_unit = models.CharField(max_length=50)
    normalized_value_tco2e = models.DecimalField(max_digits=18, decimal_places=6, help_text="Emissions in tonnes of CO2 equivalent (tCO2e)")
    
    confidence_score = models.IntegerField(help_text="Data quality score from 0-100")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='validated')
    validation_notes = models.TextField(blank=True, null=True, help_text="Reasons for review flags or anomalies")
    
    transaction_date = models.DateField(help_text="Occurred date or transaction date")
    billing_start_date = models.DateField(blank=True, null=True, help_text="Start of billing cycle (Scope 2)")
    billing_end_date = models.DateField(blank=True, null=True, help_text="End of billing cycle (Scope 2)")
    
    is_locked = models.BooleanField(default=False, help_text="True if approved/locked for audit. Cannot be edited.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date', 'facility']

    def __str__(self):
        return f"{self.facility} - {self.scope} - {self.normalized_value_tco2e} tCO2e ({self.status})"
