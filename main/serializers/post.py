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
    author_name = serializers.CharField(source='author.profile.username', read_only=True)
    visibility = serializers.ChoiceField(choices=Post.VISIBILITY_CHOICES, required=False)
    keyword = serializers.CharField(read_only=True)
    subject = serializers.ChoiceField(choices=Post.SUBJECT_CHOICES, required=False, default="주제 선택 안 함")
    total_likes = serializers.IntegerField(source="like_count", read_only=True)
    total_comments = serializers.IntegerField(source="comment_count", read_only=True)
    category_name = serializers.CharField(source="category.name", required=True)
    images = PostImageSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'author_name', 'title', 'content', 'status', 'category_name', 'subject', 'keyword',
            'visibility', 'images', 'created_at', 'updated_at', 'total_likes', 'total_comments'
        ]
        read_only_fields = ['id', 'author_name', 'created_at', 'updated_at', 'keyword', 'images']

    def extract_image_urls(self, content):
        return re.findall(r'<img\\s+[^>]*src=["\']([^"\']+)["\']', content)

    def validate_category_name(self, value):
        if not Category.objects.filter(name=value).exists():
            raise serializers.ValidationError(f"'{value}'은(는) 유효한 카테고리가 아닙니다.")
        return value

    def create(self, validated_data):
        category_name = validated_data.pop('category_name', '게시판')
        category = Category.objects.get(name=self.validate_category_name(category_name))
        validated_data['category'] = category
        post = Post.objects.create(**validated_data)

        image_urls = self.extract_image_urls(post.content)
        for url in image_urls:
            PostImage.objects.create(post=post, image=url)

        return post

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.content = validated_data.get('content', instance.content)
        instance.status = validated_data.get('status', instance.status)

        category_name = validated_data.get('category_name', instance.category.name)
        if category_name:
            category = Category.objects.get(name=self.validate_category_name(category_name))
            instance.category = category

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








