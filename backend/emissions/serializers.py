from rest_framework import serializers
from emissions.models import FacilityProfile, NormalisedEmissionRecord

# ── New canonical serializers ──────────────────────────────────────────────

class FacilityProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityProfile
        fields = '__all__'


class NormalisedEmissionRecordSerializer(serializers.ModelSerializer):
    raw_payload = serializers.SerializerMethodField()
    batch_name  = serializers.SerializerMethodField()

    class Meta:
        model  = NormalisedEmissionRecord
        fields = '__all__'

    def get_raw_payload(self, obj):
        """Expose the original source payload for audit / debug use."""
        if obj.raw_row_id:
            return obj.raw_row.raw_payload
        return None

    def get_batch_name(self, obj):
        if obj.batch_id:
            return obj.batch.name
        return None


# ── Backwards-compatible aliases (used by existing views / tests) ───────────
# These can be removed once views.py is updated to use the new names.
FacilityLookupSerializer       = FacilityProfileSerializer
NormalizedRecordSerializer     = NormalisedEmissionRecordSerializer
