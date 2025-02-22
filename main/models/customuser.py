from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from main.models.category import Category  # ✅ Category 모델 import

class CustomUserManager(BaseUserManager):
    def create_user(self, id, password=None, **extra_fields):
        if not id:
            raise ValueError("The ID field must be set")
        if not password:
            raise ValueError("The password field must be set")

        user = self.model(id=id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(id, password, **extra_fields)

class CustomUser(AbstractUser):
    username = None
    id = models.CharField(max_length=50, unique=True, primary_key=True)

    first_name = None
    last_name = None
    email = None

    objects = CustomUserManager()

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.id
