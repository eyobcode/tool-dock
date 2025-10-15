from .models import ScanJob, Finding, InputType
from rest_framework import serializers

class ScanSerializer(serializers.ModelSerializer):
    options = serializers.JSONField(required=False)

    class Meta:
        model = ScanJob
        fields = ["target", "tool", "input_type", "consent", "options"]

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError("Consent must be true to start the scan.")
        return value
    
    