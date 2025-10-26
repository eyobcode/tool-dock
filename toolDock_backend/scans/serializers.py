from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    validate_ipv46_address,
    URLValidator
)
from rest_framework import serializers
from .models import ScanJob, Tool, Finding



class FindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Finding
        fields = [
            "id",
            "severity",
            "title",
            "description",
            "category",
            "cvss_score",
            "remediation",
            "affected_component"
        ]



class ScanSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    progress = serializers.IntegerField(read_only=True)
    job_id = serializers.UUIDField(read_only=True)
    options = serializers.JSONField(write_only=True)
    input_type = serializers.CharField(write_only=True)
    consent = serializers.BooleanField(write_only=True)

    def validate(self, attrs):
        if not attrs.get('consent', False):
            raise serializers.ValidationError({"error": "User consent required for this tool."})

        tool = attrs.get('tool')
        if not tool:
            raise serializers.ValidationError({"error": "Tool is required."})

        if not settings.TOOL_RUNNERS.get(tool.name.lower()):
            raise serializers.ValidationError({"error": f"Tool '{tool.name}' is not supported."})

        input_type = attrs.get('input_type')
        if input_type and input_type not in tool.supported_input_types:
            raise serializers.ValidationError({
                "error": f"Input type '{input_type}' is not supported by '{tool.name}'. "
            })
        return attrs

    class Meta:
        model = ScanJob
        fields = [
            "job_id", 
            "target", 
            "tool",
            "input_type",
            "consent",
            "options",
            "status", 
            "progress",
            "created_at", 
        ]
    

class ScanResultSerializer(serializers.ModelSerializer):
    findings = FindingSerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()

    def get_summary(self, obj: ScanJob):
        findings = obj.findings.all() #type: ignore
        return {
            "total_findings": findings.count(),
            "critical": findings.filter(severity="critical").count(),
            "high": findings.filter(severity="high").count(),
            "medium": findings.filter(severity="medium").count(),
            "low": findings.filter(severity="low").count(),
            "info": findings.filter(severity="info").count(),
        }

    class Meta:
        model = ScanJob
        fields = [
            "job_id",
            "target",
            "tool",
            "status",
            "progress",
            "findings",
            "summary",  
            "raw_output"
        ]
