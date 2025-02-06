from rest_framework import serializers
from main.models.post import Post
from main.models.comment import Comment
from main.models.heart import Heart  # ✅ 게시글 좋아요 추가

class NewsSerializer(serializers.Serializer):
    activity_id = serializers.CharField(read_only=True)  # ✅ `activity_id` 추가
    type = serializers.CharField()  # "post_comment", "post_like", "comment_reply"
    content = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField()
    is_read = serializers.BooleanField(default=False)
    is_parent = serializers.BooleanField(read_only=True)  # ✅ 댓글/대댓글 여부 추가

    def to_representation(self, instance):
        user = self.context['request'].user  # ✅ 현재 로그인된 사용자
        activity_id = None
        activity_type = None
        content = None
        is_parent = None

        if isinstance(instance, Comment):
            if instance.post.author == user:  # ✅ 내가 작성한 게시글에 달린 댓글
                activity_id = f"comment_{instance.id}"
                activity_type = "post_comment"
                content = f"{instance.author.username}님이 '{instance.post.title}' 글에 댓글을 남겼습니다."
                is_parent = instance.is_parent  # ✅ 댓글/대댓글 여부 저장

            elif instance.parent and instance.parent.author == user.profile:  # ✅ 내가 작성한 댓글에 달린 대댓글
                activity_id = f"comment_{instance.id}"
                activity_type = "comment_reply"
                content = f"{instance.author.username}님이 '{instance.post.title}' 글에 대댓글을 남겼습니다."
                is_parent = instance.is_parent

        elif isinstance(instance, Heart):
            if instance.post.author == user:  # ✅ 내가 작성한 게시글에 달린 좋아요
                activity_id = f"heart_{instance.id}"
                activity_type = "post_like"
                content = f"{instance.user.username}님이 '{instance.post.title}' 글을 좋아합니다."

        return {
            "activity_id": activity_id,
            "type": activity_type,
            "content": content,
            "created_at": instance.created_at,
            "is_read": instance.is_read,
            "is_parent": is_parent,  # ✅ 추가
        }
