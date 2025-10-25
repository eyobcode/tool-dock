import json


from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework import status

from .models import ScanJob
from .serializers import ScanSerializer,ScanResultSerializer
from .tasks import run_scan_task



    

class ScanViewSet(CreateModelMixin, GenericViewSet):
    queryset = ScanJob.objects.select_related('findings').all()
    serializer_class = ScanSerializer

    def _parsed_options(self):
        raw_options = self.request.data.get("options") # type: ignore
        if raw_options in (None, "", "null"):
            return {}
        try:
            return json.loads(raw_options)
        except json.JSONDecodeError:
            return {}

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()


        scan_type = self._parsed_options().get("scan_type")


        if scan_type == "quick":
            result_serializer = ScanResultSerializer(job)
            run_scan_task.apply(args=[str(job.job_id)]).get()
            return Response({"ok": True, "data": result_serializer.data}, status=status.HTTP_200_OK)
        
        run_scan_task.apply(args=[str(job.job_id)])
        response_data = ScanSerializer(job).data
        return Response({"ok": True, "data": response_data}, status=status.HTTP_202_ACCEPTED)
