# utils.py
import base64
import json
import re
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

        post_image = PostImage.objects.create(
            post=post,
            image=image_file,
            caption=caption,
            is_representative=is_representative
        )
        created_images.append(post_image)

    # ✅ 2. Base64 이미지 저장 (content 내 포함된 이미지)
    content = request.data.get('content', '')
    base64_images = re.findall(r'<img.*?src=["\'](data:image/.*?;base64,.*?)["\']', content)

    for idx, img_str in enumerate(base64_images, start=len(created_images)):
        # ✅ Base64 디코딩
        format, imgstr = img_str.split(';base64,')
        ext = format.split('/')[-1]
        image_data = base64.b64decode(imgstr)
        image_file = ContentFile(image_data, name=f"post_{post.id}_base64_{idx}.{ext}")

        post_image = PostImage.objects.create(
            post=post,
            image=image_file,
            caption=f"Base64 이미지 {idx+1}",
            is_representative=False
        )
        created_images.append(post_image)

        # ✅ content 내 Base64 URL → 실제 이미지 URL로 교체
        content = content.replace(
            img_str,
            post_image.image.url
        )

    # ✅ `content`의 Base64 URL을 실제 URL로 업데이트
    post.content = content
    post.save()

    # ✅ 3. 대표사진 자동 설정 (없으면 첫 번째 이미지)
    if not any(img.is_representative for img in created_images) and created_images:
        created_images[0].is_representative = True
        created_images[0].save()

    return created_images
