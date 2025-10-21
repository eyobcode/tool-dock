from datetime import timezone as dt_timezone
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin
from rest_framework import status
from rest_framework.response import Response
from .models import ScanJob
from .serializers import ScanSerializer
from .tasks import run_scan_task
import json
import time
from collections import Counter

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

        # Start the Celery task ONCE and keep its AsyncResult
        # Step 5: Trigger background scan task
        async_res = run_scan_task.delay(str(scan_job.job_id))

        # If quick, wait briefly for the result
        # Step 4: Handle quick scan (skip Celery if needed)
        if scan_type == "quick":
            wait_seconds = 10.0  # tune this
            poll_interval = 0.5
            waited = 0.0

            while waited < wait_seconds:
                if async_res.ready():
                    try:
                        findings = async_res.get(timeout=1)  # should be the list returned by the task
                    except Exception as exc:
                        return Response({
                            "status": "failed",
                            "message": "Quick scan task failed",
                            "error": str(exc),
                            "job_id": str(scan_job.job_id)
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    # Ensure findings is a list
                    if findings is None:
                        findings = []

                    # Build summary
                    severities = [f.get("severity", "info") for f in findings]
                    cnt = Counter(severities)
                    summary = {
                        "total_findings": len(findings),
                        "critical": cnt.get("critical", 0),
                        "high": cnt.get("high", 0),
                        "medium": cnt.get("medium", 0),
                        "low": cnt.get("low", 0),
                        "info": cnt.get("info", 0),
                    }

                    return Response({
                        "ok": True,
                        "data": {
                            "job_id": str(scan_job.job_id),
                            "target": scan_job.target,
                            "tool": scan_job.tool.name,
                            "status": scan_job.status,
                            "progress": scan_job.progress,
                            "created_at": scan_job.created_at.astimezone(dt_timezone.utc)
                                .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                            "findings": findings,
                            "summary": summary,
                            "raw_output_preview": (scan_job.raw_output or "")[:200]
                        }
                    }, status=status.HTTP_200_OK)

                time.sleep(poll_interval)
                waited += poll_interval

            # timed out waiting
            return Response({
                "ok": True,
                "data": {
                    "job_id": str(scan_job.job_id),
                    "status": "running",
                    "message": "Quick scan still running; check status later."
                }
            }, status=status.HTTP_202_ACCEPTED)

        # Step 6: Normal scan response
        response_data = {
            "ok": True,
            "data": {
                "job_id": str(scan_job.job_id),
                "target": scan_job.target,
                "tool": scan_job.tool.name,
                "status": scan_job.status,
                "progress": scan_job.progress,
                "created_at": scan_job.created_at.astimezone(dt_timezone.utc)
                    .replace(microsecond=0)
                    .isoformat()
                    .replace("+00:00", "Z"),
                "estimated_duration": getattr(scan_job.tool, "estimated_duration", None)
            }
        }

        return Response(response_data, status=status.HTTP_202_ACCEPTED)
