"""
ingestion/models.py
-------------------
Data ingestion pipeline models for the Breathe ESG platform.

Design decisions
~~~~~~~~~~~~~~~~
* UploadBatch — one ingestion event from one external system.
  Acts as the provenance anchor; every RawIngestedRow links back here.
  ``source_type`` drives which parser and normalisation pipeline runs.
  ``external_ref`` stores the original filename / API batch ID so
  data can be re-ingested or traced back to its origin.

* RawIngestedRow — stores data EXACTLY as received, never modified.
  This is the legal and compliance anchor.
  - ``raw_payload`` is untyped JSON to handle the heterogeneous schemas
    from SAP XML, utility CSVs, and travel JSON feeds.
  - ``checksum`` (SHA-256 of raw_payload) prevents accidental re-ingestion
    of the same row from the same batch.
  - ``source_row_index`` maps back to the original file line for debugging.
"""

import uuid
from django.db import models
from django.utils import timezone

from tenants.models import Tenant, ESGUser
from .choices import SourceType, BatchStatus


# ─────────────────────────────────────────────
# 1. UploadBatch  (single ingestion event)
# ─────────────────────────────────────────────

class UploadBatch(models.Model):
    """
    Represents one ingestion event from one external data system.

    ``source_type`` is stored here (not on the row) because it is
    an attribute of the feed, not of individual rows within it.
    ``error_summary`` holds pipeline-level errors as structured JSON;
    row-level validation failures live on NormalisedEmissionRecord.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant       = models.ForeignKey(
        Tenant, on_delete=models.PROTECT, related_name="upload_batches"
    )
    source_type  = models.CharField(max_length=20, choices=SourceType.choices)
    name         = models.CharField(
        max_length=255,
        help_text="Human label, e.g. 'SAP Plant 42 – Oct 2024'"
    )
    external_ref = models.CharField(
        max_length=255, blank=True,
        help_text="Original filename, API batch ID, or storage key for re-ingestion traceability"
    )
    status       = models.CharField(
        max_length=20, choices=BatchStatus.choices, default=BatchStatus.PENDING
    )
    reporting_year = models.PositiveSmallIntegerField(
        help_text="Calendar or fiscal year this batch covers, e.g. 2024"
    )
    uploaded_by  = models.ForeignKey(
        ESGUser, null=True, on_delete=models.SET_NULL, related_name="uploaded_batches"
    )
    uploaded_at  = models.DateTimeField(auto_now_add=True)
    row_count    = models.PositiveIntegerField(default=0)
    # Structured JSON for pipeline-level errors (not row-level validation)
    error_summary = models.JSONField(
        null=True, blank=True,
        help_text="Pipeline errors captured during ingestion, keyed by stage"
    )

    class Meta:
        db_table = "esg_upload_batch"
        indexes  = [
            models.Index(
                fields=["tenant", "source_type", "reporting_year"],
                name="idx_batch_tenant_src_year"
            ),
            models.Index(fields=["status"], name="idx_batch_status"),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.source_type}] ({self.status})"


# ─────────────────────────────────────────────
# 2. RawIngestedRow  (immutable, source-of-truth store)
# ─────────────────────────────────────────────

class RawIngestedRow(models.Model):
    """
    Stores data EXACTLY as received from the source system — no transformation.

    Immutability contract (enforced at the service layer):
      - No UPDATE or DELETE after creation.
      - Re-ingestion of an identical payload from the same batch is rejected
        via the (batch, checksum) unique constraint.

    ``raw_payload`` is freeform JSON because SAP XML-parsed dicts look
    nothing like utility CSV rows or travel API responses. A single typed
    schema cannot represent all three without dozens of nullable columns.
    """
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant           = models.ForeignKey(
        Tenant, on_delete=models.PROTECT, related_name="raw_rows"
    )
    batch            = models.ForeignKey(
        UploadBatch, on_delete=models.PROTECT, related_name="raw_rows"
    )
    raw_payload      = models.JSONField(
        help_text="Unmodified source data — the legal and compliance anchor"
    )
    source_row_index = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Row / line number in the original file for debugging"
    )
    checksum         = models.CharField(
        max_length=64,
        help_text="SHA-256 hex digest of raw_payload for duplicate detection"
    )
    received_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "esg_raw_row"
        constraints = [
            # Prevent exact duplicate payloads within the same batch
            models.UniqueConstraint(
                fields=["batch", "checksum"],
                name="uq_raw_row_batch_checksum"
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "batch"], name="idx_raw_tenant_batch"),
            models.Index(fields=["checksum"],         name="idx_raw_checksum"),
        ]
        ordering = ["batch", "source_row_index"]

    def __str__(self) -> str:
        return f"Row {self.source_row_index} in batch {self.batch_id}"


# Backwards-compatible alias (used by parsers.py — remove once that file is updated)
RawIngestedData = RawIngestedRow
