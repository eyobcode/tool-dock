from django.db import models
from django.conf import settings
from uuid import uuid4 
from django.utils.translation import gettext_lazy as _ 



class ToolCategory(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=100,
        editable=False
    )  # e.g. "network_scanning"

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, blank=True)


    def save(self, *args, **kwargs):
        if not self.id and self.name:
            self.id = self.name.lower().replace(" ", "_")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def tool_count(self):
        return self.tools.count() # type: ignore



class Tool(models.Model):

    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    category = models.ForeignKey(
        ToolCategory,
        on_delete=models.CASCADE,
        related_name='tools'
    )
    description = models.TextField(blank=True)
    long_description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=100, blank=True)
    requires_consent = models.BooleanField(default=False)

    input_schema = models.JSONField(default=dict)
    supported_input_types = models.JSONField(default=list)

    estimated_duration = models.PositiveIntegerField(help_text="In seconds", default=0)
    difficulty = models.CharField(max_length=50)

    def __str__(self):
        return self.display_name

class ScanJob(models.Model):

    STATUS = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    job_id = models.UUIDField(primary_key=True,default=uuid4,editable=False,unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scans",null=True)
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name="scan_jobs")
    input_type = models.CharField(max_length=50)
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


