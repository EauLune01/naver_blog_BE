from django.db import models
from django.conf import settings
from slugify import slugify
from ..models.category import Category


def image_upload_path(instance, filename):
    """
    ✅ 이미지 업로드 경로 설정
    - 경로: post_pics/{post_id}/{filename}
    """
    post_id = instance.post.id or "unknown"  # post.id 사용
    ext = filename.split('.')[-1]  # 확장자 추출
    filename = f"{post_id}_{instance.pk}.{ext}"  # '게시물ID_이미지ID.확장자' 형식
    return os.path.join("post_pics", str(post_id), filename)


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
        settings.AUTH_USER_MODEL,  # ✅ CustomUser 참조
        on_delete=models.CASCADE,
        related_name="posts"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_DEFAULT,  # ✅ 삭제 시 기본값으로 변경
        default=1,  # ✅ 기본 카테고리를 '게시판'으로 설정 (없으면 자동 생성)
        related_name="posts"
    )
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default="주제 선택 안 함")
    keyword = models.CharField(max_length=50, choices=KEYWORD_CHOICES, default="default")  # ✅ 자동 분류 필드
    title = models.CharField(max_length=100)
    content = models.TextField(blank=True, null=True)  # ✅ HTML 전체 저장
    status = models.CharField(
        max_length=10,
        choices=POST_CHOICES,
        default='draft'
    )
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default='everyone',
        verbose_name="공개 범위"
    )
    like_count = models.PositiveIntegerField(default=0)  # 하트 개수 저장
    comment_count = models.PositiveIntegerField(default=0)  # 댓글 개수 저장
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_read = models.BooleanField(default=False)  # 읽음 상태 필드 추가

    def save(self, *args, **kwargs):
        """ ✅ 기본 카테고리 자동 설정 (없으면 '게시판'으로) """
        if not self.category or not Category.objects.filter(id=self.category.id).exists():
            self.category, _ = Category.objects.get_or_create(id=1, name="게시판")

        """ ✅ subject 값에 따라 keyword 자동 설정 """
        keyword_mapping = {
            "엔터테인먼트/예술": ["문학·책", "영화", "미술·디자인", "공연·전시", "음악", "드라마", "스타·연예인", "만화·애니", "방송"],
            "생활/노하우/쇼핑": ["일상·생각", "육아·결혼", "반려동물", "좋은글·이미지", "패션·미용", "인테리어/DIY", "요리·레시피", "상품리뷰", "원예/재배"],
            "취미/여가/여행": ["게임", "스포츠", "사진", "자동차", "취미", "국내여행", "세계여행", "맛집"],
            "지식/동향": ["IT/컴퓨터", "사회/정치", "건강/의학", "비즈니스/경제", "어학/외국어", "교육/학문"],
            "default": ["주제 선택 안 함"],
        }
        self.keyword = next((key for key, values in keyword_mapping.items() if self.subject in values), "default")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category} / {self.title} / {dict(self.VISIBILITY_CHOICES).get(self.visibility)}"


class PostImage(models.Model):
    """
    ✅ 게시물에 포함된 이미지 저장 모델
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=image_upload_path)  # ✅ post.id 기반 이미지 저장
    image_url = models.URLField(blank=True, null=True)  # ✅ HTML 본문 내 이미지 URL
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_representative = models.BooleanField(default=False, verbose_name="대표 사진 여부")

    def save(self, *args, **kwargs):
        """
        ✅ 이미지 저장 시 자동으로 image_url 설정
        """
        super().save(*args, **kwargs)
        if not self.image_url and self.image:
            self.image_url = self.image.url  # ✅ 경로에 맞춰 URL 자동 반영
            super().save(update_fields=["image_url"])

    def __str__(self):
        return f"Image for {self.post.title} (Representative: {self.is_representative})"