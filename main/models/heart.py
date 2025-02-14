from django.db import models
from django.conf import settings
from main.models.post import Post

class Heart(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="hearts")  # ✅ 어떤 게시글에 하트를 눌렀는지 저장
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # ✅ 누가 눌렀는지 저장
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ 하트 누른 시간
    is_read = models.BooleanField(default=False)  # ✅ 추가됨
    class Meta:
        unique_together = ('post', 'user')  # ✅ 한 사용자가 같은 게시글에 여러 번 누를 수 없도록 설정

    def __str__(self):
        return f"{self.user.username} ❤️ {self.post.title}"
