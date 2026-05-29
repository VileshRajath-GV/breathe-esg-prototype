"""
emissions/models.py
--------------------
Core emission data models for the Breathe ESG platform.

Design decisions
~~~~~~~~~~~~~~~~
* FacilityProfile — replaces the thin FacilityLookup; adds location fields
  and a link back to the tenant so facility-level reporting is possible.

* NormalisedEmissionRecord — the business-facing record produced by the
  normalisation pipeline; what analysts review, approve, and audit.

  Key choices:
  - FK to RawIngestedRow preserves the full audit chain back to source data.
  - ``period_start`` / ``period_end`` support utility billing cycles and
    travel booking windows. For point-in-time SAP records set period_end = period_start.
  - ``quantity_raw`` + ``unit_raw`` preserve what the pipeline read before conversion.
  - ``quantity_normalised`` + ``unit_normalised`` are what go into reports.
  - ``co2e_kg`` is always in kilograms so aggregation across scopes is safe.
  - ``confidence_score`` is an integer 0-100 (not an enum) so pipelines can
    express nuance and thresholds can be tuned operationally without migrations.
  - ``review_status`` drives the approval state machine (see choices.py).
  - ``locked_at`` / ``locked_by`` enforce the audit lock after APPROVED → LOCKED.

* EmissionFactor — a simple lookup table for factor versioning. Storing one
  row per factor avoids denormalised duplication across emission records and
  makes it easy to re-derive emissions when a factor is updated.
"""

import uuid
from django.db import models
from django.utils import timezone

from tenants.models import Tenant, ESGUser
from ingestion.models import UploadBatch, RawIngestedRow
from .choices import EmissionScope, ReviewStatus, NormalisedUnit
from ingestion.choices import SourceType


# ─────────────────────────────────────────────
# 1. FacilityProfile  (reference / lookup data)
# ─────────────────────────────────────────────

class FacilityProfile(models.Model):
    """
    A named physical or logical location owned by a tenant.

    ``code`` is the system-of-record identifier (e.g. SAP WERKS code '1000').
    The unique_together constraint prevents the same code appearing twice for
    the same tenant while allowing different tenants to reuse codes.
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant        = models.ForeignKey(
        Tenant, on_delete=models.PROTECT, related_name="facility_profiles"
    )
    code          = models.CharField(
        max_length=100,
        help_text="System-of-record code, e.g. SAP plant '1000' or meter ID 'MTR-992'"
    )
    name          = models.CharField(
        max_length=255,
        help_text="Human-readable name, e.g. 'Bangalore Plant A'"
    )
    address       = models.CharField(max_length=500, blank=True)
    country       = models.CharField(max_length=100, blank=True)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = "esg_facility_profile"
        unique_together = [("tenant", "code")]
        indexes         = [
            models.Index(fields=["tenant", "is_active"], name="idx_facility_tenant_active"),
        ]

    def __str__(self) -> str:
        return f"{self.tenant.name} | {self.code} → {self.name}"


# ─────────────────────────────────────────────
# 2. EmissionFactor  (versioned factor library)
# ─────────────────────────────────────────────

class EmissionFactor(models.Model):
    """
    A versioned emission conversion factor.

    Centralised lookup avoids denormalising the factor across every emission
    record. When a regulatory body (DEFRA, EPA, IPCC) publishes new values,
    update this table and re-derive affected NormalisedEmissionRecords.

    ``factor_value`` is kg CO2e per unit_from (e.g. kg CO2e / kWh).
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=255,
                                    help_text="Descriptive name, e.g. 'UK Grid Electricity 2024'")
    source       = models.CharField(
        max_length=255,
        help_text="Authoritative source, e.g. 'DEFRA 2024', 'EPA eGRID 2023', 'IPCC AR6'"
    )
    scope        = models.CharField(max_length=10, choices=EmissionScope.choices)
    activity     = models.CharField(
        max_length=150,
        help_text="Activity category, e.g. 'Stationary Combustion – Natural Gas'"
    )
    unit_from    = models.CharField(
        max_length=50,
        help_text="Input unit the factor converts from, e.g. 'kWh', 'litres', 'km'"
    )
    factor_value = models.DecimalField(
        max_digits=20, decimal_places=10,
        help_text="kg CO2e per unit_from"
    )
    valid_from   = models.PositiveSmallIntegerField(
        help_text="Reporting year this factor first applies to, e.g. 2024"
    )
    valid_to     = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Last reporting year this factor applies to; null = still current"
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "esg_emission_factor"
        indexes  = [
            models.Index(fields=["scope", "activity", "valid_from"], name="idx_factor_scope_act_year"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.factor_value} kg CO2e / {self.unit_from})"


# ─────────────────────────────────────────────
# 3. NormalisedEmissionRecord  (reviewable, auditable)
# ─────────────────────────────────────────────

class NormalisedEmissionRecord(models.Model):
    """
    The business-facing record produced by the normalisation pipeline.
    This is what analysts review, approve, and auditors inspect.

    Relationship to RawIngestedRow:
    - Typically 1:1 — one raw row produces one emission record.
    - A single invoice line spanning multiple scopes (e.g. Scope 1 + Scope 3)
      may produce multiple NormalisedEmissionRecords pointing to the same row.
    - The (raw_row, scope) unique constraint prevents accidental duplication.

    Locking invariant:
    - When review_status = LOCKED, both locked_at and locked_by must be set.
    - Enforced in the model's save() and at the service layer.
    """
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant           = models.ForeignKey(
        Tenant, on_delete=models.PROTECT, related_name="emission_records"
    )
    batch            = models.ForeignKey(
        UploadBatch, on_delete=models.PROTECT, related_name="emission_records"
    )
    raw_row          = models.ForeignKey(
        RawIngestedRow, on_delete=models.PROTECT, related_name="emission_records"
    )
    reporting_year   = models.PositiveSmallIntegerField()

    # ── Facility & temporal coverage ─────────
    facility         = models.ForeignKey(
        FacilityProfile, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="emission_records",
        help_text="Resolved facility profile (null if unresolved)"
    )
    facility_label   = models.CharField(
        max_length=255, blank=True,
        help_text="Raw facility label from source, kept for traceability even when FK is resolved"
    )
    period_start     = models.DateField(
        help_text="Start of the activity period (billing cycle start, trip departure date, etc.)"
    )
    period_end       = models.DateField(
        help_text="End of the activity period; equal to period_start for point-in-time records"
    )

    # ── Source classification ─────────────────
    source_type      = models.CharField(max_length=20, choices=SourceType.choices)
    scope            = models.CharField(max_length=10,  choices=EmissionScope.choices)
    category         = models.CharField(
        max_length=150, blank=True,
        help_text="GHG Protocol category, e.g. 'Stationary Combustion', 'Business Travel — Air'"
    )
    activity_type    = models.CharField(
        max_length=150, blank=True,
        help_text="Specific activity, e.g. 'Diesel', 'Grid Electricity', 'Short-Haul Flight'"
    )

    # ── Raw quantity (pre-normalisation) ──────
    quantity_raw     = models.DecimalField(
        max_digits=20, decimal_places=6,
        help_text="Quantity as parsed from the source before unit conversion"
    )
    unit_raw         = models.CharField(
        max_length=50,
        help_text="Unit as received from source, e.g. 'gallons', 'kBTU', 'miles'"
    )

    # ── Normalised quantity ────────────────────
    quantity_normalised = models.DecimalField(
        max_digits=20, decimal_places=6,
        help_text="Quantity after conversion to unit_normalised"
    )
    unit_normalised     = models.CharField(
        max_length=20, choices=NormalisedUnit.choices
    )

    # ── Emission calculation ──────────────────
    emission_factor        = models.DecimalField(
        max_digits=20, decimal_places=8,
        help_text="Conversion factor applied, e.g. kg CO2e / kWh"
    )
    emission_factor_ref    = models.ForeignKey(
        EmissionFactor, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="applied_records",
        help_text="FK to the versioned factor row used for this calculation"
    )
    emission_factor_source = models.CharField(
        max_length=255, blank=True,
        help_text="Textual citation, e.g. 'DEFRA 2024 Table 1A' (used when FK unavailable)"
    )
    # Always stored in kg for consistent cross-scope aggregation
    co2e_kg                = models.DecimalField(
        max_digits=20, decimal_places=4,
        help_text="Final GHG impact in kg CO2e — universal aggregation unit"
    )

    # ── Quality signals ───────────────────────
    confidence_score = models.SmallIntegerField(
        default=100,
        help_text=(
            "0–100. Calculated by the pipeline based on data completeness and source reliability. "
            "Records below the AUTO_APPROVED threshold (≥80) are routed to NEEDS_REVIEW."
        )
    )
    anomaly_flag     = models.BooleanField(
        default=False,
        help_text="True when the pipeline detects a statistical outlier"
    )
    anomaly_reason   = models.TextField(
        blank=True,
        help_text="Human-readable explanation of why the record was flagged"
    )

    # ── Review workflow ───────────────────────
    review_status  = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.NEEDS_REVIEW
    )
    reviewed_by    = models.ForeignKey(
        ESGUser, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_records"
    )
    reviewed_at    = models.DateTimeField(null=True, blank=True)
    review_notes   = models.TextField(blank=True)

    # ── Audit lock ────────────────────────────
    locked_at      = models.DateTimeField(null=True, blank=True)
    locked_by      = models.ForeignKey(
        ESGUser, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="locked_records"
    )

    # ── Metadata ──────────────────────────────
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table    = "esg_emission_record"
        constraints = [
            # One normalised record per scope per raw row — prevents double-counting
            models.UniqueConstraint(
                fields=["raw_row", "scope"],
                name="uq_emission_raw_row_scope"
            ),
            # period_end must be on or after period_start
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F("period_start")),
                name="chk_period_end_gte_start"
            ),
            models.CheckConstraint(
                condition=models.Q(confidence_score__gte=0, confidence_score__lte=100),
                name="chk_confidence_score_range"
            ),
            models.CheckConstraint(
                condition=models.Q(co2e_kg__gte=0),
                name="chk_co2e_non_negative"
            ),
        ]
        indexes = [
            # Primary dashboard aggregation axis
            models.Index(
                fields=["tenant", "reporting_year", "scope"],
                name="idx_er_tenant_year_scope"
            ),
            # Analyst review queue
            models.Index(
                fields=["tenant", "review_status"],
                name="idx_er_tenant_status"
            ),
            # Source breakdown reports
            models.Index(
                fields=["tenant", "source_type", "reporting_year"],
                name="idx_er_tenant_src_year"
            ),
            # Anomaly queue retrieval
            models.Index(fields=["anomaly_flag"], name="idx_er_anomaly"),
            # Utility billing period range queries
            models.Index(fields=["period_start", "period_end"], name="idx_er_period"),
        ]

    def save(self, *args, **kwargs):
        """
        Enforce the LOCKED invariant:
        when review_status == LOCKED both locked_at and locked_by must be set.
        """
        if self.review_status == ReviewStatus.LOCKED:
            if not self.locked_at:
                self.locked_at = timezone.now()
            if not self.locked_by_id:
                raise ValueError(
                    "locked_by must be set before a record can be moved to LOCKED status."
                )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.tenant_id} | {self.scope} | "
            f"{self.co2e_kg} kg CO2e | {self.review_status}"
        )


# ─────────────────────────────────────────────
# Backwards-compatible aliases
# (used by parsers.py / tests.py — remove once those files are updated)
# ─────────────────────────────────────────────
FacilityLookup   = FacilityProfile
NormalizedRecord = NormalisedEmissionRecord
