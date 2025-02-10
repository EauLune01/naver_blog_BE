from rest_framework import serializers
from main.models.post import Post, PostText, PostImage
from main.models.heart import Heart  # ✅ 좋아요 모델 추가
from main.models.comment import Comment  # ✅ 댓글 모델 추가


class PostTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostText
        fields = ['id', 'content', 'font', 'font_size', 'is_bold']


class PostImageSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = PostImage
        fields = ['id', 'image', 'caption', 'is_representative']


class PostSerializer(serializers.ModelSerializer):
    texts = PostTextSerializer(many=True, read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source='author.profile.username', read_only=True)
    visibility = serializers.ChoiceField(choices=Post.VISIBILITY_CHOICES)
    keyword = serializers.CharField(read_only=True)
    subject = serializers.ChoiceField(choices=Post.SUBJECT_CHOICES, default="주제 선택 안 함")

    # ✅ "총 좋아요 개수" & "총 댓글 개수"
    total_likes = serializers.IntegerField(source="like_count", read_only=True)
    total_comments = serializers.IntegerField(source="comment_count", read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'author_name', 'title', 'category', 'subject', 'keyword', 'visibility',
            'is_complete', 'texts', 'images', 'created_at', 'updated_at',
            'total_likes', 'total_comments'
        ]
        read_only_fields = ['id', 'author_name', 'created_at', 'updated_at', 'keyword']

    def validate_subject(self, value):
        """ subject 값이 유효한지 검증하고 keyword 자동 설정 """
        valid_subjects = [choice[0] for choice in Post.SUBJECT_CHOICES]
        if value not in valid_subjects:
            raise serializers.ValidationError(f"'{value}'은(는) 유효하지 않은 주제입니다.")
        return value

    def validate_visibility(self, value):
        """ visibility 값이 유효한지 검증 """
        valid_visibilities = [choice[0] for choice in Post.VISIBILITY_CHOICES]
        if value not in valid_visibilities:
            raise serializers.ValidationError(f"'{value}'은(는) 유효하지 않은 공개 범위 값입니다.")
        return value

