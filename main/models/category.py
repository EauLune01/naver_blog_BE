from django.db import models

class Category(models.Model):
    """ ✅ 블로그 카테고리 목록을 관리하는 모델 """
    name = models.CharField(max_length=50, unique=True, verbose_name="카테고리명")

    def __str__(self):
        return self.name

