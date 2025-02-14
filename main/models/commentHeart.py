from django.db import models
from django.conf import settings
from main.models.comment import Comment

class CommentHeart(models.Model):
    """ 댓글 및 대댓글의 좋아요 (하트) 관리 """
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="hearts")  # ✅ 어떤 댓글에 하트를 눌렀는지
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # ✅ 누가 눌렀는지 저장
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ 좋아요 누른 시간
    is_read = models.BooleanField(default=False)  # ✅ 추가됨

    class Meta:
        unique_together = ('comment', 'user')  # ✅ 한 유저가 하나의 댓글/대댓글에 한 번만 좋아요 가능

    def __str__(self):
        return f"{self.user.username} ❤️ {self.comment.content[:20]}"
