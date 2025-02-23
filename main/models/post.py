import uuid
import os
from django.db import models
from django.conf import settings
from ..models.category import Category

# ✅ UUID 기반 이미지 경로 생성 함수
def image_upload_path(instance, filename):
    ext = filename.split('.')[-1]  # 확장자 추출
    unique_name = uuid.uuid4().hex  # 유니크한 이름 생성
    return os.path.join("post_pics", str(instance.post.id), f"{unique_name}.{ext}")


class Post(models.Model):
    VISIBILITY_CHOICES = [
        ('everyone', '전체 공개'),
        ('mutual', '서로 이웃만 공개'),
        ('me', '나만 보기'),
    ]

    KEYWORD_CHOICES = [
        ("default", "주제 선택 안 함"),
        ("엔터테인먼트/예술", "엔터테인먼트/예술"),
        ("생활/노하우/쇼핑", "생활/노하우/쇼핑"),
        ("취미/여가/여행", "취미/여가/여행"),
        ("지식/동향", "지식/동향"),
    ]

    SUBJECT_CHOICES = [
        ("주제 선택 안 함", "주제 선택 안 함"),
        ("문학·책", "문학·책"), ("영화", "영화"), ("미술·디자인", "미술·디자인"), ("공연·전시", "공연·전시"),
        ("음악", "음악"), ("드라마", "드라마"), ("스타·연예인", "스타·연예인"), ("만화·애니", "만화·애니"), ("방송", "방송"),
        ("일상·생각", "일상·생각"), ("육아·결혼", "육아·결혼"), ("반려동물", "반려동물"), ("좋은글·이미지", "좋은글·이미지"),
        ("패션·미용", "패션·미용"), ("인테리어/DIY", "인테리어/DIY"), ("요리·레시피", "요리·레시피"), ("상품리뷰", "상품리뷰"), ("원예/재배", "원예/재배"),
        ("게임", "게임"), ("스포츠", "스포츠"), ("사진", "사진"), ("자동차", "자동차"), ("취미", "취미"),
        ("국내여행", "국내여행"), ("세계여행", "세계여행"), ("맛집", "맛집"),
        ("IT/컴퓨터", "IT/컴퓨터"), ("사회/정치", "사회/정치"), ("건강/의학", "건강/의학"),
        ("비즈니스/경제", "비즈니스/경제"), ("어학/외국어", "어학/외국어"), ("교육/학문", "교육/학문"),
    ]

    POST_CHOICES = [
        ('draft', '임시 저장'),
        ('published', '발행'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_DEFAULT,
        default=1,
        related_name="posts"
    )
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default="주제 선택 안 함")
    keyword = models.CharField(max_length=50, choices=KEYWORD_CHOICES, default="default")
    title = models.CharField(max_length=100)
    content = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=POST_CHOICES, default='draft')
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='everyone')
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_read = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.category or not Category.objects.filter(id=self.category.id).exists():
            self.category, _ = Category.objects.get_or_create(id=1, name="게시판")

        keyword_mapping = {
            "엔터테인먼트/예술": ["문학·책", "영화", "미술·디자인", "공연·전시", "음악", "드라마", "스타·연예인", "만화·애니", "방송"],
            "생활/노하우/쇼핑": ["일상·생각", "육아·결혼", "반려동물", "좋은글·이미지", "패션·미용", "인테리어/DIY", "요리·레시피", "상품리뷰", "원예/재배"],
            "취미/여가/여행": ["게임", "스포츠", "사진", "자동차", "취미", "국내여행", "세계여행", "맛집"],
            "지식/동향": ["IT/컴퓨터", "사회/정치", "건강/의학", "비즈니스/경제", "어학/외국어", "교육/학문"],
            "default": ["주제 선택 안 함"],
        }
        self.keyword = next((key for key, values in keyword_mapping.items() if self.subject in values), "default")
        super().save(*args, **kwargs)

    @property
    def absolute_url(self):
        """
        ✅ 게시물의 절대 URL 반환
        """
        site_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
        return f"{site_url}/posts/{self.id}/"

    def __str__(self):
        return f"{self.category} / {self.title} / {dict(self.VISIBILITY_CHOICES).get(self.visibility)}"


class PostImage(models.Model):
    """
    ✅ 게시물에 포함된 이미지 저장 모델
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=image_upload_path)
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_representative = models.BooleanField(default=False)

    @property
    def absolute_url(self):
        """
        ✅ 절대 URL을 반환하는 속성
        """
        site_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
        return f"{site_url}{self.image.url}" if self.image else ""

    def save(self, *args, **kwargs):
        """
        ✅ 이미지 저장 시 자동으로 image_url 설정
        """
        if not self.post.id:
            self.post.save()  # ✅ post.id가 없으면 먼저 저장
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.post.title} (Representative: {self.is_representative})"