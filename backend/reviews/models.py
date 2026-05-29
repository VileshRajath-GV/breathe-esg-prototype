import uuid
from django.db import models
from tenants.models import Tenant
from emissions.models import NormalizedRecord

class AuditTrail(models.Model):
    ACTION_CHOICES = [
        ('create', 'Record Created'),
        ('edit', 'Record Edited'),
        ('approve', 'Record Approved (Locked)'),
        ('flag', 'Record Flagged for Review'),
        ('unlock', 'Record Unlocked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='audit_trails')
    record = models.ForeignKey(NormalizedRecord, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.CharField(max_length=150, help_text="Username or email of the actor")
    performed_at = models.DateTimeField(auto_now_add=True)
    old_values = models.JSONField(blank=True, null=True, help_text="State of record before change")
    new_values = models.JSONField(blank=True, null=True, help_text="State of record after change")
    comment = models.TextField(blank=True, null=True, help_text="Rationale for the review action")

    class Meta:
        ordering = ['-performed_at']

    def __str__(self):
        return f"{self.action} on {self.record.id} by {self.performed_by} at {self.performed_at}"
