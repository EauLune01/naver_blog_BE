from rest_framework import serializers
from ..models.profile import Profile
from PIL import Image
import io

try:
    import pillow_heif  # HEIC 지원을 위한 라이브러리
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            'blog_name', 'blog_pic', 'username', 'user_pic', 'intro',
            'neighbor_visibility', 'urlname', 'urlname_edit_count'
        ]
        read_only_fields = ['urlname']
        extra_kwargs = {
            'blog_pic': {'required': False, 'allow_null': True},
            'user_pic': {'required': False, 'allow_null': True},
            'intro': {'required': False, 'allow_blank': True},
            'urlname_edit_count': {'read_only': True},  # ✅ 변경 횟수는 클라이언트가 수정 불가
        }

    def get_neighbors(self, obj):
        return [
            {"username": neighbor.username, "user_pic": neighbor.user_pic.url if neighbor.user_pic else None}
            for neighbor in obj.neighsbors.all()
        ]

    def validate_blog_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("블로그 이름은 공백일 수 없습니다.")
        if len(value) > 20:
            raise serializers.ValidationError("블로그 이름은 최대 20자까지 입력 가능합니다.")
        return value

    def validate_username(self, value):
        if not value.strip():
            raise serializers.ValidationError("사용자 이름은 공백일 수 없습니다.")
        if len(value) > 15:
            raise serializers.ValidationError("사용자 이름은 최대 15자까지 입력 가능합니다.")
        return value

    # ✅ 블로그 이미지 유효성 검증
    def validate_blog_pic(self, value):
        return self._validate_image(value, "블로그 사진")

    # ✅ 프로필 이미지 유효성 검증
    def validate_user_pic(self, value):
        return self._validate_image(value, "프로필 사진")

    # ✅ 이미지 유효성 검사 (공통 함수)
    def _validate_image(self, value, image_type):
        if value:
            # 크기 제한 (10MB 이하)
            if value.size > 10 * 1024 * 1024:  # 10MB
                raise serializers.ValidationError(f"{image_type}은 10MB 이하의 파일만 업로드할 수 있습니다.")

            # 지원하는 이미지 확장자 목록 (HEIC 포함)
            allowed_content_types = [
                "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp", "image/heic", "image/heif"
            ]

            # 확장자 검증
            if value.content_type not in allowed_content_types:
                raise serializers.ValidationError(
                    f"{image_type}은 {', '.join([ext.split('/')[-1].upper() for ext in allowed_content_types])} 형식만 지원됩니다."
                )

            # HEIC 파일이면 JPEG으로 변환
            if value.content_type in ["image/heic", "image/heif"] and pillow_heif:
                try:
                    heif_image = pillow_heif.open_heif(value)
                    image = Image.frombytes(heif_image.mode, heif_image.size, heif_image.data)

                    # 변환 후 다시 저장
                    output = io.BytesIO()
                    image.save(output, format="JPEG")
                    output.seek(0)
                    value.file = output
                    value.content_type = "image/jpeg"
                except Exception:
                    raise serializers.ValidationError(f"{image_type} 파일 변환 중 오류가 발생했습니다.")

            # 이미지 해상도 검증 (10x10 이상, 5000x5000 이하)
            try:
                image = Image.open(value)
                min_width, min_height = 10, 10
                max_width, max_height = 5000, 5000

                if image.width < min_width or image.height < min_height:
                    raise serializers.ValidationError(
                        f"{image_type}의 크기는 최소 {min_width}x{min_height} 픽셀이어야 합니다. "
                        f"(현재 크기: {image.width}x{image.height})"
                    )

                if image.width > max_width or image.height > max_height:
                    raise serializers.ValidationError(
                        f"{image_type}의 크기는 최대 {max_width}x{max_height} 픽셀까지만 가능합니다. "
                        f"(현재 크기: {image.width}x{image.height})"
                    )
            except Exception:
                raise serializers.ValidationError(f"{image_type}은 올바른 이미지 파일이 아닙니다.")

        return value

    def validate_intro(self, value):  # ✅ intro 유효성 검사
        if value and len(value) > 100:
            raise serializers.ValidationError("자기소개는 최대 100자까지 입력 가능합니다.")
        return value


class UrlnameUpdateSerializer(serializers.Serializer):
    """ ✅ `urlname`만 변경할 수 있도록 별도 시리얼라이저 생성 """
    urlname = serializers.CharField(max_length=30, required=True)

    def validate_urlname(self, value):
        """ ✅ URL 이름 변경 제한 """
        profile = self.context.get('profile')  # ✅ `ProfileUrlnameUpdateView`에서 넘긴 profile 객체
        if profile and profile.urlname_edit_count >= 1:
            raise serializers.ValidationError("URL 이름은 한 번만 변경할 수 있습니다.")
        return value



