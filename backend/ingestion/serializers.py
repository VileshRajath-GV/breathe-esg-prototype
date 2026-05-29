from rest_framework import serializers
from ingestion.models import UploadBatch, RawIngestedRow


class UploadBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UploadBatch
        fields = '__all__'


class RawIngestedRowSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RawIngestedRow
        fields = '__all__'


# Backwards-compatible alias
RawIngestedDataSerializer = RawIngestedRowSerializer
