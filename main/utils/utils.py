import base64
import json
import re
import os
from django.core.files.base import ContentFile
from main.models.post import PostImage

def save_images_from_request(post, request):
    """
    ✅ `request`에서 다중 이미지 저장 (multipart와 Base64 지원)
    ✅ `captions`, `is_representative` 처리 포함
    ✅ `PostImage` 모델에 저장
    """
    captions = json.loads(request.data.get('captions', '[]'))
    is_representative_flags = json.loads(request.data.get('is_representative', '[]'))

    # ✅ 1. Multipart (파일) 이미지 저장
    images = request.FILES.getlist('images', [])
    created_images = []

    for idx, image_file in enumerate(images):
        caption = captions[idx] if idx < len(captions) else None
        is_representative = is_representative_flags[idx] if idx < len(is_representative_flags) else False

        # ✅ 파일 확장자를 안전하게 추출
        ext = os.path.splitext(image_file.name)[-1].lower()
        if not ext:
            ext = ".png"  # 기본 확장자 설정

        post_image = PostImage.objects.create(
            post=post,
            image=image_file,
            caption=caption,
            is_representative=is_representative
        )
        created_images.append(post_image)

    # ✅ 2. Base64 이미지 저장 (content 내 포함된 이미지)
    content = request.data.get('content', '')
    base64_images = re.findall(r'<img.*?src=["\'](data:image/[a-zA-Z]+;base64,[^"\']+)["\']', content)

    base64_start_idx = len(created_images)  # 기존 업로드된 이미지 수를 기준으로 Base64 인덱스 설정

    for idx, img_str in enumerate(base64_images, start=base64_start_idx):
        try:
            # ✅ Base64 디코딩
            format, imgstr = img_str.split(';base64,')
            ext = format.split('/')[-1].lower()

            # ✅ 확장자가 올바른지 확인 후 기본값 설정
            if ext not in ["png", "jpg", "jpeg", "gif", "webp"]:
                ext = "png"

            image_data = base64.b64decode(imgstr)
            image_file = ContentFile(image_data, name=f"post_{post.id}_base64_{idx}.{ext}")

            # ✅ Base64 이미지에 대한 캡션 및 대표사진 여부 설정
            caption = captions[idx] if idx < len(captions) else f"Base64 이미지 {idx + 1}"
            is_representative = is_representative_flags[idx] if idx < len(is_representative_flags) else False

            post_image = PostImage.objects.create(
                post=post,
                image=image_file,
                caption=caption,
                is_representative=is_representative
            )
            created_images.append(post_image)

            # ✅ content 내 Base64 URL → 실제 이미지 URL로 치환
            content = content.replace(img_str, post_image.image.url)

        except Exception as e:
            print(f"❌ Base64 이미지 처리 오류: {e}")

    # ✅ `content`의 Base64 URL을 실제 URL로 업데이트
    post.content = content
    post.save()

    # ✅ 3. 대표사진 자동 설정 (없으면 첫 번째 이미지)
    if not any(img.is_representative for img in created_images) and created_images:
        created_images[0].is_representative = True
        created_images[0].save()

    return created_images


