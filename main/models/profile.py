from django.db import models
from django.conf import settings
import os


# ✅ 업로드 경로 처리 함수
def blog_pic_upload_path(instance, filename):
    return f"blog_pics/{instance.user.id}/{filename}"


def user_pic_upload_path(instance, filename):
    return f"user_pics/{instance.user.id}/{filename}"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    blog_name = models.CharField(max_length=20)
    blog_pic = models.ImageField(upload_to=blog_pic_upload_path, null=True, blank=True,
                                 default='default/blog_default.jpg')
    username = models.CharField(max_length=15, null=False, blank=False, default="Unnamed")
    user_pic = models.ImageField(upload_to=user_pic_upload_path, null=True, blank=True,
                                 default='default/user_default.jpg')
    intro = models.CharField(max_length=100, null=True, blank=True, help_text="간단한 자기소개를 입력해주세요 (최대 100자)")

    # ✅ URL 이름 (한 번만 변경 가능)
    urlname = models.CharField(max_length=30, unique=True, null=False, blank=False)
    urlname_edit_count = models.PositiveIntegerField(default=0, help_text="urlname 변경 횟수 (0: 변경 가능, 1: 변경 불가)")

    # ✅ 서로이웃 관계
    neighbors = models.ManyToManyField("self", symmetrical=True, blank=True)
    neighbor_visibility = models.BooleanField(default=True, help_text="서로이웃 목록을 공개할지 여부")

    def __str__(self):
        return f"{self.user.id} - {self.urlname}"

    def save(self, *args, **kwargs):
        """
        ✅ 프로필 사진 변경 시 기존 파일 삭제 (중복 저장 방지)
        """
        if self.pk:
            old_instance = Profile.objects.get(pk=self.pk)

            # ✅ 기존 블로그 프로필 사진 삭제
            if old_instance.blog_pic and old_instance.blog_pic != self.blog_pic:
                if old_instance.blog_pic.name != 'default/blog_default.jpg':
                    if os.path.isfile(old_instance.blog_pic.path):
                        os.remove(old_instance.blog_pic.path)

            # ✅ 기존 사용자 프로필 사진 삭제
            if old_instance.user_pic and old_instance.user_pic != self.user_pic:
                if old_instance.user_pic.name != 'default/user_default.jpg':
                    if os.path.isfile(old_instance.user_pic.path):
                        os.remove(old_instance.user_pic.path)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        ✅ Profile 삭제 방지
        """
        raise NotImplementedError("프로필은 삭제할 수 없습니다.")


