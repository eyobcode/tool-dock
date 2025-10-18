from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import RetrieveModelMixin, CreateModelMixin
from rest_framework import status
from rest_framework.response import Response
from .models import ScanJob, Finding, Tool
from .serializers import ScanSerializer


class ScanViewSet(CreateModelMixin,GenericViewSet):
    queryset = ScanJob.objects.select_related('input_type', 'tool').all()
    serializer_class = ScanSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan_job: ScanJob = serializer.save()

        response_data = {
            "ok": True,
            "data": {
                "job_id": str(scan_job.job_id),
                "target": scan_job.target,
                "tool": scan_job.tool.name,
                "status": scan_job.status,
                "progress": scan_job.progress,
                "created_at": scan_job.created_at.isoformat(),
                "estimated_duration": scan_job.tool.estimated_duration
            }
        }
        return Response(response_data, status=status.HTTP_202_ACCEPTED)