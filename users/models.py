from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.apps import apps
from django.conf import settings

class CustomUser(AbstractUser):
    is_manager = models.BooleanField(default=False)
    is_employee = models.BooleanField(default=True)

    def __str__(self):
        return self.username