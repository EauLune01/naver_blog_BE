from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings

class Category(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=50, verbose_name="카테고리명")

    class Meta:
        unique_together = ("user", "name")  # ✅ 같은 사용자가 동일한 카테고리를 중복 생성할 수 없음

    def delete(self, *args, **kwargs):
        """ ✅ '게시판' 카테고리는 삭제할 수 없도록 제한 """
        if self.name == "게시판":
            raise ValidationError("⚠️ '게시판' 카테고리는 삭제할 수 없습니다.")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.user.id} - {self.name}"

