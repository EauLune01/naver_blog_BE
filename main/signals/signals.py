from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
from main.models.profile import Profile
from main.models.comment import Comment
from main.models.post import Post


# 🛠 새로운 사용자가 생성될 때 자동으로 Profile 생성
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            blog_name=f"{instance.id}님의 블로그",
            username=instance.id,  # ✅ username 기본값
            urlname=str(instance.id),
        )


# ✅ 프로필 변경 전에 기존 값을 저장하는 딕셔너리
old_usernames = {}

@receiver(pre_save, sender=Profile)
def store_old_username(sender, instance, **kwargs):
    """ ✅ 프로필이 변경되기 전에 기존 username 저장 """
    try:
        old_instance = Profile.objects.get(pk=instance.pk)
        old_usernames[instance.pk] = old_instance.username  # ✅ 기존 username 저장
    except Profile.DoesNotExist:
        old_usernames[instance.pk] = None  # 새 프로필인 경우

@receiver(post_save, sender=Profile)
def update_comment_author_name(sender, instance, **kwargs):
    """ ✅ 프로필의 username이 변경되었을 경우, 기존 댓글의 author_name을 업데이트 """
    old_username = old_usernames.get(instance.pk)

    if old_username and old_username != instance.username:
        # ✅ 기존 댓글을 찾아 author_name을 업데이트
        comments = Comment.objects.filter(author=instance)
        for comment in comments:
            comment.author_name = instance.username
            comment.save()  # ✅ 개별 저장

        # ✅ 업데이트 후 기존 데이터 삭제
        del old_usernames[instance.pk]

@receiver(post_save, sender=Comment)
def update_comment_count_on_save(sender, instance, **kwargs):
    """ ✅ 댓글이 추가될 때 comment_count 증가 """
    post = instance.post
    post.comment_count = Comment.objects.filter(post=post).count()
    post.save(update_fields=["comment_count"])

@receiver(post_delete, sender=Comment)
def update_comment_count_on_delete(sender, instance, **kwargs):
    """ ✅ 댓글이 삭제될 때 comment_count 감소 """
    post = instance.post
    post.comment_count = Comment.objects.filter(post=post).count()
    post.save(update_fields=["comment_count"])