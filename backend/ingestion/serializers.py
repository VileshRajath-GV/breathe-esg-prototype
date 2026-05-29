from rest_framework import serializers
from ingestion.models import UploadBatch, RawIngestedData

class UploadBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadBatch
        fields = '__all__'

class RawIngestedDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawIngestedData
        fields = '__all__'
