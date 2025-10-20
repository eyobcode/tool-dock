from django.shortcuts import render
from datetime import timezone
import json
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import RetrieveModelMixin, CreateModelMixin
from rest_framework import status
from rest_framework.response import Response
from .models import ScanJob, Finding, Tool
from .serializers import ScanSerializer
from .tasks import run_scan_task


class ScanViewSet(CreateModelMixin, GenericViewSet):
    queryset = ScanJob.objects.select_related('tool').all()
    serializer_class = ScanSerializer

    def create(self, request, *args, **kwargs):
        # Validate and save the scan job
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan_job: ScanJob = serializer.save()

        options_raw = request.data.get("options")

        # Always produce a dict
        options = {}
        if isinstance(options_raw, str):
            try:
                parsed = json.loads(options_raw)
                if isinstance(parsed, dict):
                    options = parsed
            except json.JSONDecodeError:
                options = {}
        elif isinstance(options_raw, dict):
            options = options_raw
        scan_type = options.get("scan_type", "default")

        run_scan_task.delay(str(scan_job.job_id))

        # Quick scan shortcut
        # if scan_type == "quick":
        #     return Response({'Quick': 'ok'}, status=status.HTTP_201_CREATED)

        # Normal scan response
        response_data = {
            "ok": True,
            "data": {
                "job_id": str(scan_job.job_id),
                "target": scan_job.target,
                "tool": scan_job.tool.name,
                "status": scan_job.status,
                "progress": scan_job.progress,
                "created_at": scan_job.created_at.astimezone(timezone.utc)
                                .replace(microsecond=0)
                                .isoformat()
                                .replace("+00:00", "Z"),
                "estimated_duration": scan_job.tool.estimated_duration
            }
        }

        return Response(response_data, status=status.HTTP_202_ACCEPTED)
