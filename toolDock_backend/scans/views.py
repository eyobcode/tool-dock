from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import RetrieveModelMixin, CreateModelMixin
from .models import ScanJob, Finding, Tool, InputType
from .serializers import ScanSerializer


class ScanViewSet(CreateModelMixin,RetrieveModelMixin, GenericViewSet):
    queryset = ScanJob.objects.all()
    serializer_class = ScanSerializer

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    