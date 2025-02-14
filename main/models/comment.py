from django.db import models
from main.models.post import Post
from main.models.profile import Profile

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(Profile, on_delete=models.CASCADE)
    author_name = models.CharField(max_length=15)
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='replies', blank=True, null=True)
    is_parent = models.BooleanField(default=True)
    is_private = models.BooleanField(default=False)
    is_post_author = models.BooleanField(default=False)  # ✅ 게시글 작성자인지 여부 저장
    like_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # ✅ 새로 추가된 필드
    is_read = models.BooleanField(default=False)  # ✅ 읽음 상태 필드 추가

    def save(self, *args, **kwargs):
        """ ✅ 게시글 작성자 여부 자동 설정 """
        if hasattr(self.post.user, 'profile'):  # ✅ post.author → post.user 변경
            self.is_post_author = self.author == self.post.user.profile  # ✅ Profile과 Profile 비교
        else:
            self.is_post_author = False  # ✅ 예외 처리
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{'대댓글' if not self.is_parent else '댓글'} by {self.author_name} on {self.post.title}"

    def can_comment(self, user):
        """ ✅ 게시글의 공개 범위에 따라 댓글 작성 가능 여부 확인 """
        if self.post.visibility == 'everyone':
            return True  # ✅ 모두 공개 게시물
        elif self.post.visibility == 'mutual':
            return self.post.user.profile.is_mutual(user.profile)  # ✅ 서로 이웃 여부 확인
        elif self.post.visibility == 'me':
            return self.post.user.profile == user.profile  # ✅ Profile과 Profile 비교
        return False


    class Meta:
        verbose_name = "Comment"
        verbose_name_plural = "Comments"




