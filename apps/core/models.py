from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model.

    Defined before the first migration so future fields can be added without
    Django's notorious user-swap dance. Keep minimal for now.
    """

    display_name = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "core_user"
