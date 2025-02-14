from rest_framework import serializers
from main.models.comment import Comment

class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    is_post_author = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(queryset=Comment.objects.all(), required=False, allow_null=True)
    replies = serializers.SerializerMethodField()  # 대댓글을 포함시키기 위한 필드 추가

    class Meta:
        model = Comment
        fields = ['id', 'author_name', 'content', 'is_private', 'is_parent', 'is_post_author', 'parent', 'created_at', 'replies']
        read_only_fields = ['id', 'created_at', 'is_parent', 'is_post_author','author_name']

    def get_author_name(self, obj):
        if obj.author and hasattr(obj.author, 'username'):
            return obj.author.username
        return None

    def get_is_post_author(self, obj):
        """ ✅ 게시글 작성자인지 여부 """
        return obj.author == obj.post.user.profile  # ✅ post.author → post.user로 변경

    def get_replies(self, obj):
        """ ✅ 대댓글을 가져오기 위한 메소드 """
        if obj.is_parent:
            replies = Comment.objects.filter(parent=obj)
            return CommentSerializer(replies, many=True, context=self.context).data
        return []

    def create(self, validated_data):
        """ ✅ 댓글 생성 시 부모 댓글 여부 자동 설정 """
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            validated_data['author'] = request.user.profile  # ✅ user.profile을 author로 설정

        # ✅ 대댓글이면 is_parent=False로 설정
        if 'parent' in validated_data and validated_data['parent'] is not None:
            validated_data['is_parent'] = False
        else:
            validated_data['is_parent'] = True

        return super().create(validated_data)

    def to_representation(self, instance):
        """ ✅ 댓글 데이터 변환 """
        user = self.context['request'].user
        data = super().to_representation(instance)

        is_authenticated = user.is_authenticated
        is_author = is_authenticated and user.profile == instance.author
        is_post_author = is_authenticated and user.profile == instance.post.user.profile
        is_parent_author = is_authenticated and instance.parent and user.profile == instance.parent.author

        # ✅ 비밀 댓글 필터링
        if instance.is_private and not (is_author or is_post_author or is_parent_author):
            data['content'] = "비밀 댓글입니다."

        # ✅ 대댓글 필터링
        if instance.is_parent:
            serialized_replies = data.get('replies', [])
            for reply in serialized_replies:
                reply_obj = Comment.objects.get(id=reply['id'])  # 대댓글 객체 가져오기
                is_reply_author = is_authenticated and user.profile == reply_obj.author
                is_reply_post_author = is_authenticated and user.profile == reply_obj.post.user.profile
                is_reply_parent_author = is_authenticated and user.profile == instance.author

                if reply_obj.is_private and not (is_reply_author or is_reply_post_author or is_reply_parent_author):
                    reply['content'] = "비밀 댓글입니다."

        return data



