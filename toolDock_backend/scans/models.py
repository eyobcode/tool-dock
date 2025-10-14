from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from uuid import uuid4



class InputType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

