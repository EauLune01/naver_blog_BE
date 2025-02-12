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
        fields = ['id', 'image', 'caption', 'is_representative', 'image_group_id']

class PostSerializer(serializers.ModelSerializer):
    texts = PostTextSerializer(many=True, read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source='author.profile.username', read_only=True)
    visibility = serializers.ChoiceField(choices=Post.VISIBILITY_CHOICES)
    keyword = serializers.CharField(read_only=True)
    subject = serializers.ChoiceField(choices=Post.SUBJECT_CHOICES, default="주제 선택 안 함")

    image_group_ids = serializers.SerializerMethodField()  # ✅ 그룹 ID 리스트 필드

    total_likes = serializers.IntegerField(source="like_count", read_only=True)
    total_comments = serializers.IntegerField(source="comment_count", read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'author_name', 'title', 'category', 'subject', 'keyword', 'visibility',
            'is_complete', 'texts', 'images', 'created_at', 'updated_at',
            'total_likes', 'total_comments', 'image_group_ids'
        ]
        read_only_fields = ['id', 'author_name', 'created_at', 'updated_at', 'keyword']

    def get_image_group_ids(self, obj):
        """ 해당 게시물의 이미지 그룹 ID 목록 반환 """
        return list(PostImage.objects.filter(post=obj).values_list('image_group_id', flat=True))

    def create(self, validated_data):
        """ 게시물과 이미지 저장 시, 이미지 그룹 ID를 함께 저장 """
        request = self.context.get('request')
        image_group_ids = request.data.getlist('image_group_ids')  # ✅ 리스트로 가져오기
        image_group_ids = [int(x) for x in image_group_ids] if image_group_ids else []

        post = Post.objects.create(**validated_data)

        # ✅ PostImage 저장 시 그룹 ID 반영
        for idx, image_data in enumerate(request.FILES.getlist('images')):
            image_group_id = image_group_ids[idx] if idx < len(image_group_ids) else 1
            PostImage.objects.create(post=post, image=image_data, image_group_id=image_group_id)

        return post

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






