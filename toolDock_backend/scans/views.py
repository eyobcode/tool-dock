from datetime import timezone as dt_timezone
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin
from rest_framework import status
from rest_framework.response import Response
from .models import ScanJob
from .serializers import ScanSerializer,GetScanSerializer
from .tasks import run_scan_task
import uuid
from .utils import get_tool_runner
import json
import time
from collections import Counter

from collections import defaultdict
from rest_framework import status
from rest_framework.response import Response
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet
import uuid
import json
import time
from datetime import timezone as dt_timezone
from .models import ScanJob
from .serializers import ScanSerializer, GetScanSerializer
from .tasks import run_scan_task

class ScanViewSet(CreateModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = ScanJob.objects.select_related('tool').all()
    serializer_class = ScanSerializer

    def _build_response(self, ok, data=None, error=None, status_code=status.HTTP_200_OK):
        """Utility to standardize API responses."""
        response = {"ok": ok}
        if data:
            response["data"] = data
        if error:
            response["error"] = error
        return Response(response, status=status_code)

    def retrieve(self, request, *args, **kwargs):
        try:
            job = ScanJob.objects.get(pk=uuid.UUID(kwargs.get('pk')))
            serializer = GetScanSerializer(job)
            return self._build_response(True, serializer.data)
        except (ValueError, TypeError):
            return self._build_response(False, error="Invalid scan job ID", status_code=status.HTTP_400_BAD_REQUEST)
        except ScanJob.DoesNotExist:
            return self._build_response(False, error="Scan job not found", status_code=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        # Validate and save ScanJob
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan_job = serializer.save()

        # Validate tool
        try:
            get_tool_runner(request.data.get('tool'))
        except (ValueError, TypeError):
            return self._build_response(False, error="Invalid target format for selected tool", status_code=status.HTTP_400_BAD_REQUEST)

        # Parse options
        options = {}
        options_raw = request.data.get("options")
        if isinstance(options_raw, dict):
            options = options_raw
        elif isinstance(options_raw, str):
            try:
                options = json.loads(options_raw) if isinstance(json.loads(options_raw), dict) else {}
            except json.JSONDecodeError:
                pass

        # Determine scan type
        scan_type = options.get("scan_type", "default")

        # Start Celery task
        async_res = run_scan_task.delay(str(scan_job.job_id))

        # Handle quick scan
        if scan_type == "quick":
            wait_seconds, poll_interval, waited = 10.0, 0.5, 0.0
            while waited < wait_seconds:
                if async_res.ready():
                    try:
                        findings = async_res.get(timeout=1) or []
                    except Exception as exc:
                        return self._build_response(False, error=f"Quick scan task failed: {exc}", 
                                                  data={"job_id": str(scan_job.job_id)}, 
                                                  status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    # Build summary
                    severities = defaultdict(int)
                    for f in findings:
                        severities[f.get("severity", "info")] += 1
                    summary = {
                        "total_findings": len(findings),
                        "critical": severities["critical"],
                        "high": severities["high"],
                        "medium": severities["medium"],
                        "low": severities["low"],
                        "info": severities["info"],
                    }

                    return self._build_response(True, {
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
                    })

                time.sleep(poll_interval)
                waited += poll_interval

            return self._build_response(True, {
                "job_id": str(scan_job.job_id),
                "status": "running",
                "message": "Quick scan still running; check status later."
            }, status_code=status.HTTP_202_ACCEPTED)

        # Normal scan response
        return self._build_response(True, {
            "job_id": str(scan_job.job_id),
            "target": scan_job.target,
            "tool": scan_job.tool.name,
            "status": scan_job.status,
            "progress": scan_job.progress,
            "created_at": scan_job.created_at.astimezone(dt_timezone.utc)
                .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "estimated_duration": getattr(scan_job.tool, "estimated_duration", None)
        }, status_code=status.HTTP_202_ACCEPTED)
    
    
class ResultView(RetrieveModelMixin, GenericViewSet):
    pass  