from django.db import models
from django.core.exceptions import ValidationError
import sys

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="카테고리명")

    def delete(self, *args, **kwargs):
        """ ✅ '게시판' 카테고리는 삭제할 수 없도록 제한 """
        if self.name == "게시판":
            raise ValidationError("⚠️ '게시판' 카테고리는 삭제할 수 없습니다.")
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

