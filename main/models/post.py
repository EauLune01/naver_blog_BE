from django.db import models
from django.conf import settings
from slugify import slugify


def image_upload_path(instance, filename):
    """
    이미지 업로드 경로 설정.
    경로: post_pics/{user_id}/{category}/{title}/{filename}
    """
    user_id = instance.post.author.id
    category = slugify(instance.post.category)
    title = slugify(instance.post.title)
    return f"post_pics/{user_id}/{category}/{title}/{filename}"



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

    COMPLETE_CHOICES = [
        ('true', '작성 완료'),
        ('false', '임시 저장'),
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    category = models.CharField(max_length=50, default='게시판', null=True)
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default="주제 선택 안 함")
    keyword = models.CharField(max_length=50, choices=KEYWORD_CHOICES,default="default")  # ✅ 자동 분류 필드
    title = models.CharField(max_length=100)
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default='everyone',
        verbose_name="공개 범위"
    )
    is_complete = models.BooleanField(
        default=False,  # 기본값은 False (임시 저장)
        verbose_name="작성 상태"
    )
    like_count = models.PositiveIntegerField(default=0)  # 하트 개수 저장
    comment_count = models.PositiveIntegerField(default=0) # 대댓글 개수 저장
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_read = models.BooleanField(default=False)  # 읽음 상태 필드 추가

    def save(self, *args, **kwargs):
        # category가 None인 경우 기본값으로 '게시판'을 설정
        if not self.category:
            self.category = '게시판'

        """ subject 값에 따라 keyword 자동 설정 """
        keyword_mapping = {
            "엔터테인먼트/예술": ["문학·책", "영화", "미술·디자인", "공연·전시", "음악", "드라마", "스타·연예인", "만화·애니", "방송"],
            "생활/노하우/쇼핑": ["일상·생각", "육아·결혼", "반려동물", "좋은글·이미지", "패션·미용", "인테리어/DIY", "요리·레시피", "상품리뷰", "원예/재배"],
            "취미/여가/여행": ["게임", "스포츠", "사진", "자동차", "취미", "국내여행", "세계여행", "맛집"],
            "지식/동향": ["IT/컴퓨터", "사회/정치", "건강/의학", "비즈니스/경제", "어학/외국어", "교육/학문"],
            "default": ["주제 선택 안 함"],
        }
        self.keyword = next((key for key, values in keyword_mapping.items() if self.subject in values),
                                     "default")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category} / {self.title} / {dict(self.COMPLETE_CHOICES).get(self.is_complete)}"


class PostText(models.Model):
    FONT_CHOICES = [
        ('nanum_gothic', '나눔고딕'),
        ('Noto Serif Korean', 'Noto Serif Korean'),
        ('Gaegu', 'Gaegu'),
        ('Nanum Pen Script', 'Nanum Pen Script'),
        ('Black And White Picture', 'Black And White Picture'),
    ]

    FONT_SIZE_CHOICES = [11, 13, 15, 16, 19, 24, 28, 30, 34, 38]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="texts")
    content = models.TextField()
    font = models.CharField(max_length=25, choices=FONT_CHOICES, default='nanum_gothic')  # 기본값: 나눔고딕
    font_size = models.IntegerField(choices=[(size, f"{size}px") for size in FONT_SIZE_CHOICES], default=15)  # 기본값: 15
    is_bold = models.BooleanField(default=False)  # 기본값: False
    def __str__(self):
        return f"Text for {self.post.title}"


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=image_upload_path)
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_representative = models.BooleanField(default=False, verbose_name="대표 사진 여부")

    def __str__(self):
        return f"Image for {self.post.title} (Representative: {self.is_representative})"