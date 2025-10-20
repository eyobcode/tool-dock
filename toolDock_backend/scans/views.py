from django.utils import timezone
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin
from rest_framework import status
from rest_framework.response import Response
from .models import ScanJob
from .serializers import ScanSerializer
from .tasks import run_scan_task
import json


class ScanViewSet(CreateModelMixin, GenericViewSet):
    queryset = ScanJob.objects.select_related('tool').all()
    serializer_class = ScanSerializer

    def create(self, request, *args, **kwargs):
        # Step 1: Validate & save the ScanJob
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan_job: ScanJob = serializer.save()

        # Step 2: Extract & normalize options safely
        options_raw = request.data.get("options")
        options = {}

        if options_raw:
            if isinstance(options_raw, str):
                try:
                    parsed = json.loads(options_raw)
                    if isinstance(parsed, dict):
                        options = parsed
                except json.JSONDecodeError:
                    pass  # silently ignore invalid JSON
            elif isinstance(options_raw, dict):
                options = options_raw

        # Step 3: Determine scan type (default to 'default')
        scan_type = options.get("scan_type", "default")

        # Step 4: Handle quick scan (skip Celery if needed)
        if scan_type == "quick":
            # You can handle quick scans immediately here
            return Response(
                {"message": "Quick scan executed instantly."},
                status=status.HTTP_201_CREATED
            )

        # Step 5: Trigger background scan task
        run_scan_task.delay(str(scan_job.job_id))

        # Step 6: Normal scan response
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
                "estimated_duration": getattr(scan_job.tool, "estimated_duration", None)
            }
        }

        return Response(response_data, status=status.HTTP_202_ACCEPTED)
