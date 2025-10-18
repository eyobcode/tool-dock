from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from uuid import uuid4



class InputType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Tool(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    path = models.CharField(max_length=255)  # e.g., scans/tools/nmap.py
    enabled = models.BooleanField(default=True)
    estimated_duration = models.PositiveIntegerField(default=60)  # in seconds

    input_types = models.ManyToManyField(InputType, related_name='tools')

    def __str__(self):
        return self.name


class ScanJob(models.Model):

    STATUS = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    job_id = models.UUIDField(primary_key=True,default=uuid4,editable=False,unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scans",null=True)
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name="scan_jobs")
    input_type = models.ForeignKey(InputType, on_delete=models.SET_NULL, null=True, blank=True)
    target = models.CharField(max_length=255)
    consent = models.BooleanField(default=False)
    options = models.JSONField(default=dict,null=True)

    status = models.CharField(max_length=20, choices=STATUS, default='queued')
    progress = models.PositiveIntegerField(default=0)
    current_step = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    raw_output = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.tool.name} ({self.job_id})"
    
    def clean(self):
        if self.input_type and self.tool:
            if not self.tool.input_types.filter(pk=self.input_type.pk).exists():
                raise ValidationError(
                    f"{self.tool.name} does not support '{self.input_type.name}' input type."
                )

class Finding(models.Model):
    job = models.ForeignKey(ScanJob, on_delete=models.CASCADE, related_name="findings")
    severity = models.CharField(max_length=10, default='info')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    cvss_score = models.FloatField(default=0.0)
    cve_ids = models.JSONField(default=list, blank=True)
    port = models.IntegerField(null=True, blank=True)
    protocol = models.CharField(max_length=10, blank=True)
    service = models.CharField(max_length=50, blank=True)
    version = models.CharField(max_length=100, blank=True)
    remediation = models.TextField(blank=True)
    references = models.JSONField(default=list, blank=True)
    affected_component = models.CharField(max_length=255, blank=True)
