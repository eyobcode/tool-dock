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


