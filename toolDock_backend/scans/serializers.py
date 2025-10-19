from .models import ScanJob, Finding
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

    def validate(self, data):
        tool = data.get("tool")
        input_type = data.get("input_type")
        if tool and input_type and input_type not in tool.supported_input_types:
            raise serializers.ValidationError({
                "input_type": f"{input_type} not supported by {tool.name}."
            })
        return data
