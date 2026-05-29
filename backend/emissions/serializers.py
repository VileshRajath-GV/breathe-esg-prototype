from rest_framework import serializers
from emissions.models import FacilityLookup, NormalizedRecord

class FacilityLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityLookup
        fields = '__all__'

class NormalizedRecordSerializer(serializers.ModelSerializer):
    raw_payload = serializers.SerializerMethodField()
    batch_filename = serializers.SerializerMethodField()

    class Meta:
        model = NormalizedRecord
        fields = '__all__'

    def get_raw_payload(self, obj):
        if obj.raw_data:
            return obj.raw_data.raw_payload
        return None

    def get_batch_filename(self, obj):
        if obj.batch:
            return obj.batch.filename
        return None
