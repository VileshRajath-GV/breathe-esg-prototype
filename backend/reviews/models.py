"""
reviews/models.py
------------------
Audit trail and review comment models for the Breathe ESG platform.

Design decisions
~~~~~~~~~~~~~~~~
* AuditEntry — append-only log of every meaningful state change.
  Uses generic (object_type, object_id) referencing instead of tight FKs
  so a single table can track changes to NormalisedEmissionRecord,
  UploadBatch, ESGUser, etc. without proliferating tables.
  Trade-off: no FK enforcement — orphan entries are possible; clean up at
  the service layer. Accepted because this is a compliance log, not a join.

  ``before_value`` / ``after_value`` are JSON so the log schema is
  decoupled from the EmissionRecord schema — a migration on EmissionRecord
  does not require a matching migration here.

* ReviewComment — structured comments attached to a specific emission record,
  separate from the audit log so analysts can have threaded discussions
  without polluting the immutable audit trail.
"""

import uuid
from django.db import models
from django.utils import timezone

from tenants.models import Tenant, ESGUser
from emissions.models import NormalisedEmissionRecord


# ─────────────────────────────────────────────
# 1. AuditEntry  (append-only, generic change log)
# ─────────────────────────────────────────────

class AuditEntry(models.Model):
    """
    Immutable record of every meaningful change to any ESG platform object.

    ``object_type`` + ``object_id`` form a generic reference that avoids
    tight FK coupling. Query with:
        AuditEntry.objects.filter(object_type="NormalisedEmissionRecord", object_id=<pk>)

    ``action`` uses an open-ended CharField (not a choices enum) so new
    pipeline stages can emit log entries without a schema migration.
    Common values: STATUS_CHANGE, FIELD_EDIT, LOCK, REJECT, INGEST, COMMENT.

    ``field_name`` is empty for multi-field or lifecycle actions (e.g. LOCK).
    """

    # Common action constants — used by service layer, not enforced by DB
    ACTION_STATUS_CHANGE = "STATUS_CHANGE"
    ACTION_FIELD_EDIT    = "FIELD_EDIT"
    ACTION_LOCK          = "LOCK"
    ACTION_REJECT        = "REJECT"
    ACTION_INGEST        = "INGEST"
    ACTION_COMMENT       = "COMMENT"

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant       = models.ForeignKey(
        Tenant, on_delete=models.PROTECT, related_name="audit_entries"
    )

    # Generic reference — avoids a separate audit table per model
    object_type  = models.CharField(
        max_length=100,
        help_text="Model name of the changed object, e.g. 'NormalisedEmissionRecord'"
    )
    object_id    = models.UUIDField(help_text="Primary key of the changed object")

    action       = models.CharField(
        max_length=50,
        help_text="e.g. STATUS_CHANGE, FIELD_EDIT, LOCK, REJECT, INGEST"
    )
    performed_by = models.ForeignKey(
        ESGUser, null=True, on_delete=models.SET_NULL, related_name="audit_entries"
    )
    performed_at = models.DateTimeField(default=timezone.now, db_index=True)

    # Field-level delta (empty for multi-field or lifecycle actions)
    field_name   = models.CharField(
        max_length=100, blank=True,
        help_text="Which field changed; empty for multi-field actions"
    )
    before_value = models.JSONField(
        null=True, blank=True,
        help_text="State before the change (typed as JSON to decouple from model schema)"
    )
    after_value  = models.JSONField(
        null=True, blank=True,
        help_text="State after the change"
    )

    # Free-text context (analyst rationale, pipeline messages)
    note         = models.TextField(blank=True)

    class Meta:
        db_table = "esg_audit_entry"
        indexes  = [
            models.Index(fields=["object_type", "object_id"], name="idx_audit_object"),
            models.Index(fields=["tenant",       "performed_at"], name="idx_audit_tenant_time"),
            models.Index(fields=["performed_by"],                 name="idx_audit_actor"),
        ]
        ordering = ["-performed_at"]

    def __str__(self) -> str:
        return (
            f"{self.action} on {self.object_type}:{self.object_id} "
            f"by {self.performed_by_id} at {self.performed_at}"
        )


# ─────────────────────────────────────────────
# 2. ReviewComment  (threaded analyst discussion)
# ─────────────────────────────────────────────

class ReviewComment(models.Model):
    """
    Analyst comment attached to a specific NormalisedEmissionRecord.

    Separate from AuditEntry because comments are mutable (can be edited /
    resolved) and are not part of the immutable compliance audit trail.
    ``is_resolved`` lets reviewers mark threads as addressed without deleting
    the comment history.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant       = models.ForeignKey(
        Tenant, on_delete=models.PROTECT, related_name="review_comments"
    )
    record       = models.ForeignKey(
        NormalisedEmissionRecord, on_delete=models.CASCADE, related_name="comments"
    )
    author       = models.ForeignKey(
        ESGUser, null=True, on_delete=models.SET_NULL, related_name="review_comments"
    )
    body         = models.TextField()
    is_resolved  = models.BooleanField(
        default=False,
        help_text="True when the comment thread has been addressed"
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "esg_review_comment"
        indexes  = [
            models.Index(fields=["record", "is_resolved"], name="idx_comment_record_resolved"),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Comment by {self.author_id} on record {self.record_id}"


# Backwards-compatible alias (used by older views — remove once those are updated)
AuditTrail = AuditEntry
