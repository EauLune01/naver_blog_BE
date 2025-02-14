from rest_framework import serializers
from main.models.post import Post, PostImage
from main.models.category import Category
import re


class PostImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PostImage
        fields = ['id', 'image', 'image_url']

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None


class PostSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.profile.username', read_only=True)  # ✅ user_name 필드 추가
    visibility = serializers.ChoiceField(choices=Post.VISIBILITY_CHOICES, required=False)
    keyword = serializers.CharField(read_only=True)
    subject = serializers.ChoiceField(choices=Post.SUBJECT_CHOICES, required=False, default="주제 선택 안 함")
    total_likes = serializers.IntegerField(source="like_count", read_only=True)
    total_comments = serializers.IntegerField(source="comment_count", read_only=True)
    category_name = serializers.SerializerMethodField()  # ✅ `source="category.name"` → `get_category_name()`
    images = PostImageSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'user_name', 'title', 'content', 'status', 'category_name', 'subject', 'keyword',
            'visibility', 'images', 'created_at', 'updated_at', 'total_likes', 'total_comments'
        ]
        read_only_fields = ['id', 'user_name', 'created_at', 'updated_at', 'keyword', 'images']

    def get_category_name(self, obj):
        """ ✅ `category.name`이 없을 경우 기본값 '게시판'을 반환 """
        return obj.category.name if obj.category else "게시판"

    def extract_image_urls(self, content):
        """ ✅ HTML `content`에서 `<img>` 태그의 `src` 속성을 찾아 반환 """
        return re.findall(r'<img\s+[^>]*src=["\']([^"\']+)["\']', content)

    def validate_category_name(self, value):
        """ ✅ 카테고리 유효성 검사 """
        if not Category.objects.filter(name=value).exists():
            raise serializers.ValidationError(f"'{value}'은(는) 유효한 카테고리가 아닙니다.")
        return value

    def create(self, validated_data):
        """ ✅ 게시물 생성 시 `category_name`을 `category`로 변환 """
        category_name = validated_data.pop('category_name', '게시판')

        # ✅ `get_or_create()`를 사용하여 없으면 자동 생성
        category, _ = Category.objects.get_or_create(name=category_name)
        validated_data['category'] = category

        post = Post.objects.create(**validated_data)

        # ✅ 본문에서 이미지 URL 추출 후 PostImage 생성
        image_urls = self.extract_image_urls(post.content)
        for url in image_urls:
            PostImage.objects.create(post=post, image=url)

        return post

    def update(self, instance, validated_data):
        """ ✅ 게시물 업데이트 로직 """
        instance.title = validated_data.get('title', instance.title)
        instance.content = validated_data.get('content', instance.content)
        instance.status = validated_data.get('status', instance.status)

        # ✅ `category_name`이 변경되었을 경우 업데이트
        category_name = validated_data.get('category_name', instance.category.name)
        if category_name:
            category, _ = Category.objects.get_or_create(name=self.validate_category_name(category_name))
            instance.category = category

        # ✅ 기존 본문의 이미지 URL & 새로운 본문의 이미지 URL 비교 후 삭제/추가
        old_image_urls = set(self.extract_image_urls(instance.content))
        new_image_urls = set(self.extract_image_urls(validated_data.get("content", instance.content)))

        stored_images = PostImage.objects.filter(post=instance)
        stored_image_urls = set(img.image for img in stored_images)

        images_to_delete = stored_image_urls - new_image_urls
        PostImage.objects.filter(post=instance, image__in=images_to_delete).delete()

        images_to_add = new_image_urls - stored_image_urls
        for url in images_to_add:
            PostImage.objects.create(post=instance, image=url)

        instance.save()
        return instance









