import re
from rest_framework import serializers
from main.models.post import Post, PostImage
from main.models.category import Category


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'image', 'caption', 'is_representative']

    def to_representation(self, instance):
        """
        ✅ 이미지 URL, 캡션, 대표사진 여부를 포함한 데이터 반환
        """
        representation = super().to_representation(instance)
        if instance.image:
            representation['image_url'] = instance.image.url
        return representation


class PostSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.profile.username', read_only=True)
    visibility = serializers.ChoiceField(choices=Post.VISIBILITY_CHOICES, required=False)
    keyword = serializers.CharField(read_only=True)
    subject = serializers.ChoiceField(choices=Post.SUBJECT_CHOICES, required=False, default="주제 선택 안 함")
    total_likes = serializers.IntegerField(source="like_count", read_only=True)
    total_comments = serializers.IntegerField(source="comment_count", read_only=True)
    category_name = serializers.SerializerMethodField()
    images = PostImageSerializer(many=True, read_only=True)
    content = serializers.SerializerMethodField()  # 🔥 `content` 필드를 수정하여 반환
    url_name = serializers.CharField(source='user.profile.urlname', read_only=True)  # 🔥 user.profile.urlname을 urlname으로 반환

    class Meta:
        model = Post
        fields = [
            'id', 'user_name', 'url_name','title', 'content', 'status', 'category_name', 'subject', 'keyword',
            'visibility', 'images', 'created_at', 'updated_at', 'total_likes', 'total_comments'
        ]
        read_only_fields = ['id', 'user_name', 'url_name','created_at', 'updated_at', 'keyword', 'images']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else "게시판"

    def get_content(self, obj):
        """
        ✅ `content` 내 `<input>` 태그를 제거하고 `caption`을 적용한 최종 HTML 반환
        """
        content = obj.content
        images = obj.images.all()  # 게시물의 모든 이미지 가져오기

        for image in images:
            # 🔥 <figcaption> 내부의 <input> 태그를 이미지의 실제 캡션으로 변환
            input_pattern = f'<input[^>]*id="caption_{image.id}"[^>]*>'
            caption_text = image.caption if image.caption else ""
            content = re.sub(input_pattern, caption_text, content)

            # 🔥 content 내 <img> 태그 URL을 절대 URL로 변경
            if image.image:
                content = content.replace(image.image.url, image.image.url)

        return content

    def create(self, validated_data):
        request = self.context.get('request')
        category_name = request.data.get('category_name', '게시판')

        try:
            category = request.user.categories.get(name=category_name)
        except Category.DoesNotExist:
            raise serializers.ValidationError(f"'{category_name}'은(는) 유효한 카테고리가 아닙니다.")

        validated_data['category'] = category
        post = Post.objects.create(**validated_data)

        from main.utils import save_images_from_request
        save_images_from_request(post, request)

        return post

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.content = validated_data.get('content', instance.content)
        instance.status = validated_data.get('status', instance.status)

        request = self.context.get('request')
        category_name = request.data.get('category_name', instance.category.name)
        if category_name:
            try:
                category = request.user.categories.get(name=category_name)
                instance.category = category
            except Category.DoesNotExist:
                raise serializers.ValidationError(f"'{category_name}'은(는) 유효한 카테고리가 아닙니다.")

        instance.save()
        return instance
