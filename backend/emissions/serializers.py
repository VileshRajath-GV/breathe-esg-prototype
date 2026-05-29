from rest_framework import serializers
from emissions.models import FacilityProfile, NormalisedEmissionRecord
from emissions.choices import ReviewStatus

# ── New canonical serializers ──────────────────────────────────────────────

class FacilityProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityProfile
        fields = '__all__'


class NormalisedEmissionRecordSerializer(serializers.ModelSerializer):
    # ── Extra computed fields for audit modal ──────────────────────────────
    raw_payload    = serializers.SerializerMethodField()
    batch_name     = serializers.SerializerMethodField()

    # ── Backwards-compat aliases for the React frontend ───────────────────
    # Frontend reads these old field names — adding them as computed fields
    # means zero frontend changes are required.
    facility              = serializers.SerializerMethodField()   # was FK UUID, now returns label
    normalized_value_tco2e = serializers.SerializerMethodField()  # was tCO2e, now derived from co2e_kg
    status                = serializers.SerializerMethodField()   # was 'validated'/'review'/'error'
    validation_notes      = serializers.SerializerMethodField()   # was CharField, now review_notes
    transaction_date      = serializers.SerializerMethodField()   # was DateField, now period_start
    is_locked             = serializers.SerializerMethodField()   # was BooleanField, now LOCKED status

    class Meta:
        model  = NormalisedEmissionRecord
        fields = '__all__'

    # ── Computed field implementations ─────────────────────────────────────

    def get_raw_payload(self, obj):
        if obj.raw_row_id:
            return obj.raw_row.raw_payload
        return None

    def get_batch_name(self, obj):
        return obj.batch.name if obj.batch_id else None

    def get_facility(self, obj):
        """Return human-readable label instead of UUID."""
        if obj.facility_label:
            return obj.facility_label
        if obj.facility_id:
            return obj.facility.name
        return 'Unknown Facility'

    def get_normalized_value_tco2e(self, obj):
        """Convert kg CO2e → tCO2e for the frontend display."""
        if obj.co2e_kg is not None:
            return float(obj.co2e_kg) / 1000
        return 0.0

    def get_status(self, obj):
        """Map new ReviewStatus choices back to the old strings the frontend expects."""
        mapping = {
            ReviewStatus.AUTO_APPROVED: 'validated',
            ReviewStatus.APPROVED:      'validated',
            ReviewStatus.LOCKED:        'validated',
            ReviewStatus.NEEDS_REVIEW:  'review',
            ReviewStatus.REJECTED:      'error',
        }
        return mapping.get(obj.review_status, 'review')

    def get_validation_notes(self, obj):
        """Return review_notes (new field) under the old key."""
        parts = []
        if obj.review_notes:
            parts.append(obj.review_notes)
        if obj.anomaly_reason:
            parts.append(obj.anomaly_reason)
        return '; '.join(filter(None, parts)) or 'Ingestion successful. No anomalies flagged.'

    def get_transaction_date(self, obj):
        """Return period_start as the display date."""
        return obj.period_start.isoformat() if obj.period_start else None

    def get_is_locked(self, obj):
        """True only when review_status == LOCKED."""
        return obj.review_status == ReviewStatus.LOCKED


# ── Backwards-compatible aliases (used by existing views / tests) ───────────
FacilityLookupSerializer   = FacilityProfileSerializer
NormalizedRecordSerializer = NormalisedEmissionRecordSerializer
