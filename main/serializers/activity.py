from rest_framework import serializers
from main.models.post import Post
from main.models.comment import Comment
from main.models.heart import Heart
from main.models.commentHeart import CommentHeart

class ActivitySerializer(serializers.Serializer):
    activity_id = serializers.SerializerMethodField()
    type = serializers.CharField()
    content = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    is_read = serializers.BooleanField()  # ✅ 이제 바로 사용 가능!
    is_parent = serializers.SerializerMethodField()
    post_id = serializers.IntegerField(read_only=True)  # ✅ post의 id 추가
    post_urlname = serializers.CharField(read_only=True)  # ✅ post의 urlname 추가

    def get_activity_id(self, obj):
        if isinstance(obj, Heart):
            return f"heart_{obj.id}"
        elif isinstance(obj, CommentHeart):
            return f"comment_heart_{obj.id}"
        elif isinstance(obj, Comment):
            return f"comment_{obj.id}"
        return f"unknown_{obj.id}"

    def get_is_parent(self, obj):
        return obj.is_parent if isinstance(obj, Comment) else None

    def to_representation(self, instance):
        username = None
        content = None
        post_id = None
        post_urlname = None

        if isinstance(instance, Comment):
            username = instance.author.username
            content = instance.content
            post_id = instance.post.id
            post_urlname = instance.post.user.profile.urlname  # ✅ post의 urlname
        elif isinstance(instance, Heart):
            username = instance.user.profile.username
            content = f"{instance.post.title} 글을 좋아합니다."
            post_id = instance.post.id
            post_urlname = instance.post.user.profile.urlname  # ✅ post의 urlname
        elif isinstance(instance, CommentHeart):
            username = instance.user.profile.username
            content = f"{instance.comment.content} 댓글을 좋아합니다."
            post_id = instance.comment.post.id
            post_urlname = instance.comment.post.user.profile.urlname  # ✅ post의 urlname

        return {
            "activity_id": self.get_activity_id(instance),
            "type": "liked_post" if isinstance(instance, Heart) else
                    "liked_comment" if isinstance(instance, CommentHeart) else
                    ("written_comment" if instance.is_parent else "written_reply"),
            "content": content,
            "created_at": instance.created_at,
            "is_read": instance.is_read,  # ✅ 이제 그대로 사용 가능!
            "is_parent": self.get_is_parent(instance),
            "post_id": post_id,
            "post_urlname": post_urlname,
        }
