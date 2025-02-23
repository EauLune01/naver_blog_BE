from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..models import Post, PostImage,CustomUser,Profile,Category
from ..models.neighbor import Neighbor
from django.db.models import Q
from ..serializers import PostSerializer
import json
import os
import shutil
from rest_framework.exceptions import NotFound,MethodNotAllowed, ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import now, timedelta
from pickle import FALSE
from main.utils.utils import save_images_from_request

def to_boolean(value):
    """
    'true', 'false', 1, 0 같은 값을 실제 Boolean(True/False)로 변환
    """
    if isinstance(value, bool):  # 이미 Boolean이면 그대로 반환
        return value
    if isinstance(value, str):
        return value.lower() == "true"  # "true" → True, "false" → False
    if isinstance(value, int):
        return bool(value)  # 1 → True, 0 → False
    return False  # 기본적으로 False 처리

class PostListView(ListAPIView):
    """
    ✅ 게시물 목록 조회 API
    - 서로이웃 공개 글과 전체 공개 글을 조회할 수 있음
    - 쿼리 파라미터: urlname, category_name, pk, keyword로 필터링 가능
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get_queryset(self):
        urlname = self.request.query_params.get('urlname', None)
        category = self.request.query_params.get('category', None)  # ✅ category_name → category로 변경
        pk = self.request.query_params.get('pk', None)
        keyword = self.request.query_params.get('keyword', None)

        # ✅ category만 존재할 경우 에러 처리
        if category and not (urlname or pk):
            raise ValidationError("카테고리만 입력된 경우는 허용하지 않습니다.")

        # ✅ keyword는 단독으로 사용해야 함
        if keyword and (urlname or category or pk):
            raise ValidationError("keyword는 단독으로 사용해야 합니다.")

        request_user = self.request.user  # ✅ API 요청을 보낸 유저

        # ✅ 전체 공개 게시물 (자기 글 제외)
        public_posts = Post.objects.filter(status="published", visibility="everyone").exclude(user=request_user)

        # ✅ 서로이웃 공개 게시물 (자기 글 제외)
        mutual_posts = Post.objects.filter(
            status="published",
            visibility="mutual",
            user__profile__neighbors=request_user.profile
        ).exclude(user=request_user)

        # ✅ 특정 사용자의 게시물 조회 (`urlname`이 주어진 경우)
        if urlname:
            profile = Profile.objects.filter(urlname=urlname).select_related("user").first()
            if not profile:
                return Post.objects.none()  # 존재하지 않는 경우 빈 쿼리셋 반환
            profile_user = profile.user
            queryset = Post.objects.filter(user=profile_user, status="published").exclude(user=request_user)
        else:
            queryset = (public_posts | mutual_posts).distinct()  # ✅ 중복 제거!

        # ✅ keyword 필터링
        if keyword:
            if keyword not in dict(Post.KEYWORD_CHOICES):
                raise ValidationError(f"'{keyword}'은(는) 유효하지 않은 keyword 값입니다.")
            return queryset.filter(keyword=keyword)

        # ✅ 특정 카테고리 필터링 (이름을 `category`로 변경)
        if category:
            try:
                category_obj = Category.objects.get(name=category)  # ✅ category → category_obj로 변경
                queryset = queryset.filter(category=category_obj)
            except Category.DoesNotExist:
                return Post.objects.none()  # 존재하지 않는 카테고리일 경우 빈 쿼리셋 반환

        # ✅ 특정 pk 필터링
        if pk:
            queryset = queryset.filter(pk=pk)

        return queryset.order_by('-created_at')  # 🔥 최신순 정렬 추가

    @swagger_auto_schema(
        operation_summary="게시물 목록 조회",
        operation_description="서로이웃 공개인 글과, 전체 공개 글을 조회할 수 있습니다. "
                              "쿼리 파라미터 urlname, category_name, pk, keyword로 필터링 가능합니다.",
        manual_parameters=[
            openapi.Parameter(
                'urlname', openapi.IN_QUERY,
                description="조회할 사용자의 URL 이름",
                required=False,
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'category_name', openapi.IN_QUERY,
                description="조회할 게시물 카테고리 이름",
                required=False,
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'pk', openapi.IN_QUERY,
                description="조회할 게시물 ID",
                required=False,
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'keyword', openapi.IN_QUERY,
                description="조회할 주제 키워드 (단독 사용 가능)",
                required=False,
                type=openapi.TYPE_STRING,
                enum=[choice[0] for choice in getattr(Post, 'KEYWORD_CHOICES', [])]  # ✅ `getattr()`로 안전 처리
            ),
        ],
        responses={200: PostSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        pk = self.request.query_params.get('pk', None)
        if pk:
            post = get_object_or_404(queryset, pk=pk)
            serializer = self.get_serializer(post)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PostCreateView(CreateAPIView):
    """
    게시물 생성 뷰
    - 사용자의 CustomUser 모델에 등록된 카테고리 중에서 카테고리 '이름'으로만 선택 가능
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = PostSerializer


    @swagger_auto_schema(
        operation_summary="게시물 생성",
        operation_description="사용자의 카테고리 중에서 '이름'으로 선택해 게시물을 생성합니다.",
        responses={201: PostSerializer()},
    )
    def post(self, request, *args, **kwargs):
        user = request.user  # ✅ 변경된 부분
        title = request.data.get('title')
        category_name = request.data.get('category_name')  # ✅ 카테고리 이름으로 선택
        subject = request.data.get('subject', '주제 선택 안 함')
        content = request.data.get('content', '')
        post_status = request.data.get('status', 'published') # ✅ Post 모델의 status 사용
        visibility = request.data.get('visibility', 'everyone')  # ✅ visibility 추가
        created_at = request.data.get('created_at')  # ✅ created_at 추가
        captions = json.loads(request.data.get('captions', '[]'))
        is_representative = json.loads(request.data.get('is_representative', '[]'))

        if not title:
            return Response({"error": "제목은 필수 항목입니다."}, status=400)

        if category_name:
            try:
                category = user.categories.get(name=category_name)  # ✅ 변경된 부분
            except Category.DoesNotExist:
                return Response({"error": f"'{category_name}'은(는) 유효하지 않은 카테고리입니다."}, status=400)
        else:
            category = user.categories.first()  # ✅ 변경된 부분

        print(request.data.get('captions'))

        post = Post.objects.create(
            user=user,  # ✅ 변경된 부분
            title=title,
            category=category,
            subject=subject,
            content=content,
            status=post_status,
            visibility = visibility,
            created_at = created_at or timezone.now()  # 기본값 설정
        )

        save_images_from_request(post, request)


        print("✅ 게시물 생성 완료:", post)

        # ✅ 이미지 저장 처리
        serializer = PostSerializer(post)

        if post_status == "published":
            return Response({"message": "게시물이 성공적으로 생성되었습니다.", "post": serializer.data}, status=201)
        elif post_status == "draft":
            return Response({"message": "게시물이 임시 저장되었습니다.", "post": serializer.data}, status=201)
        else:
            return Response({"error": "게시물 상태가 유효하지 않습니다."}, status=400)

class PostMyView(ListAPIView):
    """
    ✅ 로그인한 사용자가 작성한 모든 게시물 목록을 조회하는 API
    - 쿼리 파라미터: category_name / pk로 필터링 가능
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_queryset(self):
        user = self.request.user
        category = self.request.query_params.get('category', None)
        pk = self.request.query_params.get('pk', None)

        # ✅ 본인이 작성한 `published` 상태의 게시물만 조회
        queryset = Post.objects.filter(user=user, status="published")

        # ✅ 'category_name'으로 필터링
        if category:
            queryset = queryset.filter(category=category)

        # ✅ 특정 pk의 게시물 조회
        if pk:
            queryset = queryset.filter(pk=pk)

        queryset = queryset.order_by('-created_at')

        return queryset

    @swagger_auto_schema(
        operation_summary="내가 작성한 게시물 목록 조회",
        operation_description="로그인된 사용자가 작성한 모든 게시물 목록을 반환합니다. "
                              "쿼리 파라미터를 이용해 category와 pk로 필터링할 수 있습니다.",
        responses={200: PostSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="게시물의 카테고리 이름으로 필터링합니다. 예: 'Travel', 'Food' 등.",
                required=False,
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'pk',
                openapi.IN_QUERY,
                description="게시물 ID로 필터링합니다.",
                required=False,
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PostMyDetailView(RetrieveAPIView):
    """
    ✅ 로그인한 사용자가 작성한 특정 게시물의 상세 정보를 조회하는 API
    - 게시물 ID(`pk`)로 조회
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer
    queryset = Post.objects.all()

    def get_object(self):
        user = self.request.user
        pk = self.kwargs.get('pk')

        if not pk:
            raise NotFound("게시물 ID가 필요합니다.")

        return get_object_or_404(Post, user=user, pk=pk, status="published")

    @swagger_auto_schema(
        operation_summary="내가 작성한 게시물 상세 조회",
        operation_description="로그인한 사용자가 특정 게시물의 상세 정보를 조회합니다.",
        responses={200: PostSerializer()},
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="게시물 ID",
                required=True,
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PostMyRecentView(RetrieveAPIView):
    """
    ✅ 로그인한 사용자가 작성한 게시물 중 n번째 최신 `published` 상태인 게시물 조회 API
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_object(self):
        user = self.request.user
        n = self.request.query_params.get("n", "1")  # 쿼리 파라미터에서 `n` 가져오기 (기본값: 1)

        # n이 숫자인지 확인하고 정수 변환
        try:
            n = int(n)
            if n < 1:
                raise ValueError
        except ValueError:
            raise ValidationError("n은 1 이상의 정수여야 합니다.")

        # 현재 로그인한 사용자의 `published` 상태인 게시물 중 최신순으로 n번째 게시물 가져오기
        posts = Post.objects.filter(user=user, status='published').order_by('-created_at')

        if len(posts) < n:
            raise NotFound(f"출판된 게시물이 {n}개 미만입니다.")

        return posts[n - 1]  # 0-based index

    @swagger_auto_schema(
        operation_summary="내가 작성한 가장 최근 게시물 조회",
        operation_description="로그인한 사용자가 작성한 게시물 중 `published` 상태이며, `n`번째 최신 게시물을 조회합니다. "
                              "`n`을 쿼리 파라미터로 입력하면 n번째 최신 게시물을 가져옵니다. (기본값: 1)",
        manual_parameters=[
            openapi.Parameter(
                'n', openapi.IN_QUERY,
                description="가져올 n번째 최신 게시물 (1부터 시작)",
                required=False,
                type=openapi.TYPE_INTEGER
            ),
        ],
        responses={200: PostSerializer()},
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PostMutualListView(ListAPIView):
    """
    ✅ 최근 1주일 내 작성된 '서로 이웃 공개' 게시물을 조회하는 API
    - `visibility='mutual'` 또는 `visibility='everyone'`인 게시물만 조회
    - **본인 게시물 제외**
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_queryset(self):
        user = self.request.user

        # ✅ 서로이웃 ID 리스트 가져오기
        from_neighbors = list(
            Neighbor.objects.filter(from_user=user, status="accepted").values_list('to_user', flat=True)
        )
        to_neighbors = list(
            Neighbor.objects.filter(to_user=user, status="accepted").values_list('from_user', flat=True)
        )
        neighbor_ids = set(from_neighbors + to_neighbors)
        neighbor_ids.discard(user.id)  # ✅ 본인 ID 제거

        # ✅ 최근 1주일 이내 작성된 글만 조회
        one_week_ago = timezone.now() - timedelta(days=7)

        # ✅ 서로이웃 + 전체 공개 글만 필터링
        queryset = Post.objects.filter(
            Q(user_id__in=neighbor_ids) &  # ✅ 서로이웃이 작성한 글
            Q(visibility__in=['mutual', 'everyone']) &  # ✅ '서로이웃 공개' or '전체 공개'
            Q(status="published") &  # ✅ 'published' 상태의 글만
            Q(created_at__gte=one_week_ago)  # ✅ 최근 7일 이내 작성된 글
        ).exclude(user=user)  # ✅ 본인 게시물 제외

        # ✅ 최신순 정렬 추가
        return queryset.order_by('-created_at')

    @swagger_auto_schema(
        operation_summary="서로이웃 게시물 목록 조회",
        operation_description="최근 1주일 내 작성된 서로이웃 공개 게시물을 조회합니다.",
        responses={200: PostSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PostMutualDetailView(RetrieveAPIView):

    permission_classes=[IsAuthenticated]
    serializer_class=PostSerializer

    def get_queryset(self):
        user = self.request.user

        # ✅ 서로이웃 ID 리스트 가져오기
        from_neighbors = list(
            Neighbor.objects.filter(from_user=user, status="accepted").values_list('to_user', flat=True)
        )
        to_neighbors = list(
            Neighbor.objects.filter(to_user=user, status="accepted").values_list('from_user', flat=True)
        )
        neighbor_ids = set(from_neighbors + to_neighbors)
        neighbor_ids.discard(user.id)  # ✅ 본인 ID 제거

        # ✅ 서로이웃 + 전체 공개 글만 필터링
        queryset = Post.objects.filter(
            Q(user_id__in=neighbor_ids) &  # ✅ 서로이웃이 작성한 글
            Q(visibility__in=['mutual', 'everyone']) &  # ✅ '서로이웃 공개' or '전체 공개'
            Q(status="published")  # ✅ 'published' 상태의 글만
        ).exclude(user=user)  # ✅ 본인 게시물 제외

        return queryset

    @swagger_auto_schema(
        operation_summary="서로이웃 게시물 상세 조회",
        operation_description="서로이웃 또는 전체 공개 게시물의 상세 정보를 조회합니다.",
        responses={200: PostSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        post = get_object_or_404(queryset, id=self.kwargs["pk"])
        serializer = self.get_serializer(post)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PostDetailView(RetrieveAPIView):
    """
    게시물 상세 조회 뷰
    """
    permission_classes = [IsAuthenticated]
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user

        # ✅ 서로이웃 ID 리스트 가져오기
        from_neighbors = list(
            Neighbor.objects.filter(from_user=user, status="accepted").values_list('to_user', flat=True)
        )
        to_neighbors = list(
            Neighbor.objects.filter(to_user=user, status="accepted").values_list('from_user', flat=True)
        )

        neighbor_ids = set(from_neighbors + to_neighbors)
        neighbor_ids.discard(user.id)  # ❌ 본인 ID 제외

        mutual_neighbor_posts = Q(visibility='mutual', user_id__in=neighbor_ids)  # ✅ 서로 이웃 게시물
        public_posts = Q(visibility='everyone')  # ✅ 전체 공개 게시물

        # ❌ 자신의 글 제외하고 필터링
        queryset = Post.objects.filter(
            (public_posts | mutual_neighbor_posts) & Q(status="published")
        ).exclude(user=user)  # ❌ 본인 게시물 제외

        return queryset

    @swagger_auto_schema(
        operation_summary="게시물 상세 조회",
        operation_description="특정 게시물의 텍스트와 이미지를 포함한 상세 정보를 조회합니다. PUT, PATCH, DELETE 요청은 허용되지 않습니다.",
        responses={200: PostSerializer()},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class PostManageView(UpdateAPIView, DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer
    queryset = Post.objects.all()
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="게시물 부분 수정 (PATCH)",
        operation_description="기존 게시물을 덮어쓰기 방식으로 수정합니다. 기존 이미지는 전부 삭제되고, 새로운 이미지가 추가됩니다.",
        manual_parameters=[
            openapi.Parameter('title', openapi.IN_FORM, description='게시물 제목', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('content', openapi.IN_FORM, description='게시물 본문 (HTML 포함)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('category_name', openapi.IN_FORM, description='카테고리 이름', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('subject', openapi.IN_FORM, description='게시물 주제', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('visibility', openapi.IN_FORM, description='공개 범위', type=openapi.TYPE_STRING, enum=['everyone', 'mutual', 'me'], required=False),
            openapi.Parameter('status', openapi.IN_FORM, description='게시물 상태 (published 또는 draft)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('captions', openapi.IN_FORM, description='이미지 캡션 배열 (JSON 형식 문자열)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('is_representative', openapi.IN_FORM, description='대표 사진 여부 배열 (JSON 형식 문자열)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('images', openapi.IN_FORM, description='새로 추가할 이미지 파일 배열', type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_FILE), required=False),
        ],
        responses={200: PostSerializer()},
    )
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        # ✅ 기본 필드 업데이트
        instance.title = request.data.get("title", instance.title)
        instance.content = request.data.get("content", instance.content)
        instance.status = request.data.get("status", instance.status)
        instance.visibility = request.data.get("visibility", instance.visibility)
        instance.subject = request.data.get("subject", instance.subject)

        # ✅ 카테고리 업데이트
        category_name = request.data.get("category_name")
        if category_name:
            category = user.categories.filter(name=category_name).first()
            if not category:
                return Response({"error": f"'{category_name}'은(는) 존재하지 않는 카테고리입니다."}, status=400)
            instance.category = category

        instance.updated_at = now()
        instance.save()

        # ✅ 기존 이미지 삭제 (전체 삭제 후 다시 추가)
        instance.images.all().delete()

        # ✅ 새로운 이미지 저장
        save_images_from_request(instance, request)

        # ✅ 응답 반환 (업데이트된 게시물 데이터)
        serializer = PostSerializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    from django.shortcuts import get_object_or_404
    from rest_framework.response import Response
    from rest_framework import status
    import os

    @swagger_auto_schema(
        operation_summary="게시물 삭제",
        operation_description="특정 게시물과 관련 이미지를 포함한 모든 데이터를 삭제합니다.",
        responses={204: "삭제 성공", 403: "권한 없음", 404: "게시물 없음"},
    )
    def delete(self, request, *args, **kwargs):
        """
        ✅ 게시물 삭제 (보완 버전)
        - 게시물 및 관련 이미지 삭제
        """
        instance = get_object_or_404(Post, id=kwargs.get("pk"))

        # ✅ 권한 체크
        if instance.user != request.user:
            return Response({"error": "게시물을 삭제할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ 이미지 삭제 (파일 존재 여부 확인 후 삭제)
        for image in instance.images.all():
            if image.image and os.path.exists(image.image.path):
                image.image.delete()  # 실제 파일 삭제
            image.delete()  # DB 레코드 삭제

        # ✅ 게시물 삭제
        instance.delete()

        return Response({"message": "게시물이 삭제되었습니다."}, status=status.HTTP_200_OK)  # 200 반환

class DraftPostListView(ListAPIView):
    """
    임시 저장된 게시물만 반환하는 뷰
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    @swagger_auto_schema(
        operation_summary="임시 저장된 게시물 목록 조회",
        operation_description="로그인한 사용자의 임시 저장된 게시물만 반환합니다.",
        responses={200: PostSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        """
        요청한 사용자의 임시 저장된 게시물만 반환
        """
        return Post.objects.filter(user=self.request.user, status="draft")  # ✅ Boolean 값으로 필터링


class DraftPostDetailView(RetrieveAPIView):
    """
    특정 임시 저장된 게시물 1개 반환하는 뷰
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    @swagger_auto_schema(
        operation_summary="임시 저장된 게시물 상세 조회",
        operation_description="특정 임시 저장된 게시물의 상세 정보를 반환합니다.",
        responses={200: PostSerializer()},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        """
        요청한 사용자의 특정 임시 저장된 게시물만 반환
        """
        return Post.objects.filter(user=self.request.user, status="draft")


class PostMyCurrentView(ListAPIView):
    """
    로그인된 유저가 작성한 최신 5개 게시물 목록을 조회하는 API
    ✅ 로그인된 유저가 작성한 게시물 중 status="published"인 게시물만 조회
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_queryset(self):
        user = self.request.user
        # ✅ is_complete=True 조건 추가
        return Post.objects.filter(user=user, status="published").order_by('-created_at')[:5]

    @swagger_auto_schema(
        operation_summary="내가 작성한 최근 5개 게시물 조회",
        operation_description="로그인된 유저가 작성한 게시물 중 status=published인 상태에서 최근 5개만 반환합니다.",
        responses={200: PostSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PostPublicCurrentView(ListAPIView):
    """
    ✅ 특정 사용자의 최신 5개 게시물을 조회하는 API (서로이웃 여부 고려)
    """
    permission_classes = [AllowAny]  # ✅ 비로그인 사용자도 조회 가능
    serializer_class = PostSerializer

    def get_queryset(self):
        """
        ✅ 특정 사용자의 블로그 게시물 중 서로이웃 여부에 따라 'mutual' 공개 포함 여부 결정
        """
        urlname = self.kwargs.get("urlname")  # 조회 대상 블로그 (사용자) ID
        viewer = self.request.user  # 현재 API를 호출하는 사용자

        # ✅ 조회 대상 블로그 주인 찾기 (Profile → User)
        profile = get_object_or_404(Profile.objects.select_related("user"), urlname=urlname)
        blog_owner = profile.user  # ✅ 해당 블로그 주인의 User 객체

        # ✅ 본인이 자신의 블로그를 조회하는 경우 모든 게시물 조회
        if viewer == blog_owner:
            return Post.objects.filter(
                user=blog_owner,
                status="published"
            ).order_by("-created_at")[:5]

        # ✅ 서로이웃 여부 확인
        is_mutual = Neighbor.objects.filter(
            (Q(from_user=viewer, to_user=blog_owner) | Q(from_user=blog_owner, to_user=viewer)),
            status="accepted"
        ).exists()

        # ✅ 공개 범위 조건 설정
        if is_mutual:
            visibility_filter = Q(visibility="everyone") | Q(visibility="mutual")  # ✅ 가독성 개선
        else:
            visibility_filter = Q(visibility="everyone")

        # ✅ 게시물 가져오기 (최근 5개)
        post_status = "published"  # ✅ 기존 `status` 변수와 겹치는 문제 해결
        return Post.objects.filter(
            visibility_filter,
            user=blog_owner,
            status=post_status,  # ✅ `status` 변수명이 아닌 `post_status` 사용하여 문제 방지
        ).order_by("-created_at")[:5]

    @swagger_auto_schema(
        operation_summary="타인의 블로그에서 최신 5개 게시물 조회",
        operation_description="특정 사용자의 블로그에서 최근 5개의 게시물을 가져옵니다. "
                              "서로이웃일 경우 'mutual'까지 포함하고, 아니라면 'everyone' 공개 글만 반환합니다.",
        responses={200: PostSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=200)

class PostCountView(APIView):
    """
    ✅ 특정 사용자의 게시물 개수를 반환하는 API
    - 본인이 조회하는 경우: **임시저장 제외 모든 글 개수**
    - 타인이 조회하는 경우:
        - **서로이웃이면 '전체 공개 + 서로이웃 공개' 게시물 개수**
        - **서로이웃이 아니면 '전체 공개' 게시물 개수**
    - 로그인하지 않은 사용자가 조회하는 경우:
        - **전체 공개(`everyone`) 게시물 개수만 반환**
    """
    permission_classes = [AllowAny]  # ✅ 인증 없이 접근 가능 (서로이웃 여부에 따라 결과 달라짐)

    @swagger_auto_schema(
        operation_summary="사용자의 게시물 개수 조회",
        operation_description="특정 사용자의 블로그에 작성된 글의 개수를 가져옵니다. "
                              "로그인한 본인이 자신의 블로그를 조회하는 경우, 서로이웃이 조회하는 경우, "
                              "서로이웃이 아닌 사용자가 조회하는 경우 모두 고려하여 반영.",
    )
    def get(self, request, urlname, *args, **kwargs):
        """
        ✅ GET 요청을 통해 특정 사용자의 게시물 개수 반환
        """
        profile = get_object_or_404(Profile, urlname=urlname)
        blog_owner = profile.user
        current_user = request.user if request.user.is_authenticated else None

        # ✅ 로그인하지 않은 사용자가 조회하는 경우 → 전체 공개 게시물만 세서 반환
        if not current_user:
            post_count = Post.objects.filter(
                user=blog_owner, status="published", visibility="everyone"
            ).count()
            return Response({"urlname": urlname, "post_count": post_count})

        # ✅ 본인이 자신의 블로그를 조회하는 경우 → 모든 `published` 상태 게시물 개수 반환
        if current_user == blog_owner:
            post_count = Post.objects.filter(user=blog_owner, status="published").count()
            return Response({"urlname": urlname, "post_count": post_count})

        # ✅ 서로이웃 관계 확인
        is_neighbor = Neighbor.objects.filter(
            (Q(from_user=current_user, to_user=blog_owner) |
             Q(from_user=blog_owner, to_user=current_user)),
            status="accepted"
        ).exists()

        # ✅ 서로이웃이면 '전체 공개 + 서로이웃 공개' 게시물 개수 반환
        if is_neighbor:
            post_count = Post.objects.filter(
                user=blog_owner,
                status="published",
                visibility__in=["everyone", "mutual"]
            ).count()
        else:
            # ✅ 서로이웃이 아니면 '전체 공개' 게시물 개수만 반환
            post_count = Post.objects.filter(
                user=blog_owner,
                status="published",
                visibility="everyone"
            ).count()

        return Response({"urlname": urlname, "post_count": post_count})