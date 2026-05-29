from rest_framework import serializers
from reviews.models import AuditEntry, ReviewComment


class AuditEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model  = AuditEntry
        fields = '__all__'


class ReviewCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ReviewComment
        fields = '__all__'


# Backwards-compatible alias
AuditTrailSerializer = AuditEntrySerializer
