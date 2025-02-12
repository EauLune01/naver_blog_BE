from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..models import Post, PostText, PostImage,CustomUser,Profile
from ..models.neighbor import Neighbor
from django.db.models import Q
from ..serializers import PostSerializer
import json
import os
import shutil
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from django.shortcuts import get_object_or_404
from django.utils.timezone import now, timedelta
from pickle import FALSE

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
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get_queryset(self):
        urlname = self.request.query_params.get('urlname', None)
        category = self.request.query_params.get('category', None)
        pk = self.request.query_params.get('pk', None)
        keyword = self.request.query_params.get('keyword', None)

        # ✅ category만 존재할 경우 에러 처리
        if category and not (urlname or pk):
            raise ValidationError("카테고리만 입력된 경우는 허용하지 않습니다.")

        # ✅ keyword는 단독으로 사용해야 함
        if keyword and (urlname or category or pk):
            raise ValidationError("keyword는 단독으로 사용해야 합니다.")

        user = self.request.user

        if urlname:
            try:
                profile = Profile.objects.get(urlname=urlname)
                user = profile.user
            except Profile.DoesNotExist:
                return Post.objects.none()

        # ✅ keyword가 주어진 경우, 해당 카테고리의 게시물만 필터링
        if keyword:
            if keyword not in dict(Post.KEYWORD_CHOICES):
                raise ValidationError(f"'{keyword}'은(는) 유효하지 않은 keyword 값입니다.")
            return Post.objects.filter(keyword=keyword, is_complete=True).exclude(
                author=user)  # ❌ 본인 게시물 제외

        # ❌ 자신의 게시물(my_posts) 제외
        from_neighbors = list(
            Neighbor.objects.filter(from_user=user, status="accepted").values_list('to_user', flat=True)
        )
        to_neighbors = list(
            Neighbor.objects.filter(to_user=user, status="accepted").values_list('from_user', flat=True)
        )
        neighbor_ids = set(from_neighbors + to_neighbors)
        neighbor_ids.discard(user.id)  # ❌ 자신의 ID 제거

        mutual_neighbor_posts = Q(visibility='mutual', author_id__in=neighbor_ids)  # ✅ 서로 이웃의 'mutual' 공개 글
        public_posts = Q(visibility='everyone')  # ✅ 전체 공개 글

        queryset = Post.objects.filter(
            (public_posts | mutual_neighbor_posts) & Q(is_complete=True)  # ✅ 자신의 글 제외
        ).exclude(author=user)  # ❌ 본인 게시물 확실하게 제거

        if category:
            queryset = queryset.filter(category=category)

        if pk:
            queryset = queryset.filter(pk=pk)

        return queryset

    @swagger_auto_schema(
        operation_summary="게시물 목록 조회",
        operation_description="서로이웃 공개인 글과, 전체 공개 글을 조회할 수 있습니다. 쿼리 파라미터 urlname, category, pk, keyword로 필터링 가능합니다.",
        manual_parameters=[
            openapi.Parameter('urlname', openapi.IN_QUERY, description="조회할 사용자의 고유 ID", required=False, type=openapi.TYPE_STRING),
            openapi.Parameter('category', openapi.IN_QUERY, description="조회할 게시물 카테고리", required=False, type=openapi.TYPE_STRING),
            openapi.Parameter('pk', openapi.IN_QUERY, description="조회할 게시물 ID", required=False, type=openapi.TYPE_INTEGER),
            openapi.Parameter('keyword', openapi.IN_QUERY, description="조회할 주제 키워드 (단독 사용 가능)",
                              required=False, type=openapi.TYPE_STRING,
                              enum=[choice[0] for choice in Post.KEYWORD_CHOICES]),
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
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = PostSerializer

    @swagger_auto_schema(
        operation_summary="게시물 생성 (multipart/form-data 사용)",
        operation_description="게시물을 생성할 때 JSON 데이터와 이미지를 함께 업로드할 수 있습니다.",
        manual_parameters=[
            openapi.Parameter('title', openapi.IN_FORM, description='게시물 제목', type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('category', openapi.IN_FORM, description='카테고리', type=openapi.TYPE_STRING,
                              required=False),
            openapi.Parameter('subject', openapi.IN_FORM, description='주제 (네이버 제공 소주제)', type=openapi.TYPE_STRING,
                              enum=[choice[0] for choice in Post.SUBJECT_CHOICES], required=False),
            openapi.Parameter('visibility', openapi.IN_FORM, description='공개 범위', type=openapi.TYPE_STRING,
                              enum=['everyone', 'mutual', 'me'], required=False),
            openapi.Parameter('is_complete', openapi.IN_FORM, description='작성 상태', type=openapi.TYPE_BOOLEAN,
                              enum=['true', 'false'], required=False),
            openapi.Parameter('texts', openapi.IN_FORM, description='텍스트 배열 (JSON 형식 문자열)', type=openapi.TYPE_STRING,
                              required=False),
            openapi.Parameter('fonts', openapi.IN_FORM, description='글씨체 배열 (JSON 형식 문자열)', type=openapi.TYPE_STRING,
                              required=False),
            openapi.Parameter('font_sizes', openapi.IN_FORM, description='글씨 크기 배열 (JSON 형식 문자열)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('is_bolds', openapi.IN_FORM, description='글씨 굵기 배열 (JSON 형식 문자열)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('images', openapi.IN_FORM, description='이미지 파일 배열', type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_FILE), required=False),
            openapi.Parameter('image_group_ids', openapi.IN_FORM, description='이미지가 속한 그룹을 나타내는 배열 (각 이미지마다 개별 입력)',
                              type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), required=False),
            openapi.Parameter('captions', openapi.IN_FORM, description='이미지 캡션 배열 (JSON 형식 문자열)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('is_representative', openapi.IN_FORM, description='대표 사진 여부 배열 (JSON 형식 문자열)',
                              type=openapi.TYPE_STRING, required=False),
        ],
        responses={201: PostSerializer()},
    )
    def post(self, request, *args, **kwargs):
        def parse_json_field(field):
            """ JSON 문자열을 리스트로 변환 """
            if field:
                try:
                    return json.loads(field)
                except json.JSONDecodeError:
                    return []
            return []

        title = request.data.get('title')
        category = request.data.get('category')
        subject = request.data.get('subject', '주제 선택 안 함')
        visibility = request.data.get('visibility', 'everyone')
        is_complete = request.data.get('is_complete', False) in ['true', True]

        texts = parse_json_field(request.data.get('texts'))
        fonts = parse_json_field(request.data.get('fonts'))
        font_sizes = parse_json_field(request.data.get('font_sizes'))
        is_bolds = parse_json_field(request.data.get('is_bolds'))
        captions = parse_json_field(request.data.get('captions'))
        is_representative_flags = parse_json_field(request.data.get('is_representative'))

        images = request.FILES.getlist('images')  # 이미지 리스트

        image_group_ids = request.data.getlist('image_group_ids')  # 리스트로 직접 받음

        # ✅ 쉼표로 구분된 문자열이면 리스트로 변환
        if len(image_group_ids) == 1 and isinstance(image_group_ids[0], str) and "," in image_group_ids[0]:
            image_group_ids = image_group_ids[0].split(",")

        # ✅ 정수 리스트로 변환
        image_group_ids = [int(x) for x in image_group_ids] if image_group_ids else []

        # ✅ 대표 이미지 체크 (True가 2개 이상이면 에러 발생)
        if is_representative_flags.count(True) > 1:
            return Response({"error": "대표 이미지는 한 개만 설정할 수 있습니다."}, status=400)

        # ✅ 모든 그룹이 False일 경우 첫 번째 그룹을 대표로 설정
        if is_representative_flags.count(True) == 0 and len(is_representative_flags) > 0:
            is_representative_flags[0] = True  # 첫 번째 그룹을 대표로 설정

        post = Post.objects.create(
            author=request.user,
            title=title,
            category=category,
            subject=subject,
            visibility=visibility,
            is_complete=is_complete
        )

        # ✅ 텍스트 저장 (글씨체, 크기, 굵기 포함)
        for idx, text in enumerate(texts):
            font = fonts[idx] if idx < len(fonts) else "nanum_gothic"
            font_size = font_sizes[idx] if idx < len(font_sizes) else 15
            is_bold = is_bolds[idx] if idx < len(is_bolds) else False
            PostText.objects.create(post=post, content=text, font=font, font_size=font_size, is_bold=is_bold)

        # ✅ 이미지 그룹 저장
        created_images = []
        group_caption_map = {}  # 그룹별 caption 저장
        group_representative_map = {}  # 그룹별 대표 이미지 설정

        for idx, img in enumerate(images):
            group_id = image_group_ids[idx] if idx < len(image_group_ids) else 1  # 그룹 ID 할당
            caption = captions[idx] if idx < len(captions) else None
            is_representative = is_representative_flags[idx] if idx < len(is_representative_flags) else False

            # ✅ 같은 그룹이면 첫 번째 등장하는 caption과 is_representative 값을 저장
            if group_id not in group_caption_map:
                group_caption_map[group_id] = caption
                group_representative_map[group_id] = is_representative  # ✅ 대표 여부도 그룹 내 동일하게 설정

            post_image = PostImage.objects.create(
                post=post,
                image=img,
                caption=group_caption_map[group_id],  # ✅ 그룹 내 동일한 caption 적용
                is_representative=group_representative_map[group_id],  # ✅ 그룹 내 동일한 대표 여부 적용
                image_group_id=group_id  # 그룹 ID 설정
            )
            created_images.append(post_image)

        # ✅ 대표 이미지 체크 (True가 2개 이상이면 에러 발생)
        if is_representative_flags.count(True) > 1:
            return Response({"error": "대표 이미지는 한 개만 설정할 수 있습니다."}, status=400)

        # ✅ 최종적으로 대표 이미지가 하나도 없으면 첫 번째 그룹의 첫 번째 이미지를 대표로 설정
        if not any(img.is_representative for img in created_images):
            created_images[0].is_representative = True
            created_images[0].save()

        serializer = PostSerializer(post)
        return Response(
            {"message": "게시물이 성공적으로 생성되었습니다." if is_complete else "게시물이 임시 저장되었습니다.", "post": serializer.data},
            status=201
        )


class PostMyView(ListAPIView):
    """
    로그인된 유저가 작성한 모든 게시물 목록을 조회하는 API
    쿼리 파라미터로 category와 pk를 통해 필터링 가능
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_queryset(self):
        user = self.request.user
        category = self.request.query_params.get('category', None)
        pk = self.request.query_params.get('pk', None)

        # ✅ 로그인된 유저가 작성한 게시물 중 is_complete=True인 게시물만 조회
        queryset = Post.objects.filter(author=user, is_complete=True)

        # 'category' 파라미터가 있으면 해당 카테고리로 필터링
        if category:
            queryset = queryset.filter(category=category)

        # 'pk' 파라미터가 있으면 해당 게시물 ID로 필터링
        if pk:
            queryset = queryset.filter(pk=pk)

        return queryset

    @swagger_auto_schema(
        operation_summary="내가 작성한 게시물 목록 조회",
        operation_description="로그인된 유저가 작성한 모든 게시물 목록을 반환합니다. 쿼리 파라미터로 category와 pk를 통해 필터링 가능합니다.",
        responses={200: PostSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="게시물의 카테고리로 필터링합니다. 예: 'Travel', 'Food' 등.",
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

class PostMyCurrentView(ListAPIView):
    """
    로그인된 유저가 작성한 최신 5개 게시물 목록을 조회하는 API
    ✅ 로그인된 유저가 작성한 게시물 중 is_complete=True인 게시물만 조회
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_queryset(self):
        user = self.request.user
        # ✅ is_complete=True 조건 추가
        return Post.objects.filter(author=user, is_complete=True).order_by('-created_at')[:5]

    @swagger_auto_schema(
        operation_summary="내가 작성한 최근 5개 게시물 조회",
        operation_description="로그인된 유저가 작성한 게시물 중 is_complete=True인 상태에서 최근 5개만 반환합니다.",
        responses={200: PostSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PostMyDetailView(RetrieveAPIView):
    """
    로그인된 유저가 작성한 특정 게시물의 상세 정보를 조회하는 API
    쿼리 파라미터가 아닌 게시물 ID로만 조회 가능
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer
    queryset = Post.objects.all()  # 기본적인 Post 객체 조회
    parser_classes = [MultiPartParser, FormParser]  # 필요시 추가

    swagger_fake_view = True  # Swagger 문서 생성을 위한 가짜 뷰 추가

    def get_object(self):
        user = self.request.user
        pk = self.kwargs.get('pk')

        if pk is None:
            raise NotFound("게시물 ID가 필요합니다.")

        return get_object_or_404(Post, author=user, pk=pk, is_complete=True)

    @swagger_auto_schema(
        operation_summary="내가 작성한 게시물 상세 조회",
        operation_description="로그인된 유저가 작성한 특정 게시물의 상세 정보를 조회합니다.",
        responses={200: PostSerializer()},
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="게시물 ID를 입력합니다.",
                required=True,
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        GET 메서드로 게시물의 상세 정보를 조회하는 로직
        """
        instance = self.get_object()  # QuerySet이 아닌 단일 객체 반환
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PostMutualView(ListAPIView):

    """
        최근 1주일 내 작성된 서로 이웃 공개 게시물을 조회
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
        neighbor_ids.discard(user.id)

        mutual_neighbor_posts = Q(author_id__in=neighbor_ids) & (Q(visibility='mutual') | Q(visibility='everyone'))

        one_week_ago = now() - timedelta(days=7)

        # ✅ 최근 1주일 이내 작성된 서로 이웃의 게시물만 반환
        queryset = Post.objects.filter(
            mutual_neighbor_posts & Q(is_complete=True) & Q(created_at__gte=one_week_ago)
        )

        return queryset

    @swagger_auto_schema(
        operation_summary="서로 이웃 게시물 목록",
        operation_description="최근 1주일 내 작성된 서로 이웃 공개 게시물을 조회합니다.",
        responses={200: PostSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
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

        mutual_neighbor_posts = Q(visibility='mutual', author_id__in=neighbor_ids)  # ✅ 서로 이웃 게시물
        public_posts = Q(visibility='everyone')  # ✅ 전체 공개 게시물

        # ❌ 자신의 글 제외하고 필터링
        queryset = Post.objects.filter(
            (public_posts | mutual_neighbor_posts) & Q(is_complete=True)
        ).exclude(author=user)  # ❌ 본인 게시물 제외

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
    queryset = Post.objects.all()  # ✅ 누락된 queryset 추가
    parser_classes = [MultiPartParser, FormParser]  # ✅ 누락된 parser_classes 추가

    def get_queryset(self):
        user = self.request.user
        return Post.objects.filter(author=user)  # ✅ 본인이 작성한 게시물만 수정/삭제 가능

    @swagger_auto_schema(
        operation_summary="게시물 전체 수정 (사용 불가)",
        operation_description="PUT 메서드는 허용되지 않습니다. 대신 PATCH를 사용하세요.",
        responses={405: "PUT method is not allowed. Use PATCH instead."},
    )
    def put(self, request, *args, **kwargs):
        return Response({"error": "PUT method is not allowed. Use PATCH instead."}, status=405)

    @swagger_auto_schema(
        operation_summary="게시물 부분 수정 (PATCH)",
        operation_description="게시물의 특정 필드만 수정합니다. 제공된 데이터만 업데이트됩니다.",
        manual_parameters=[
            openapi.Parameter('title', openapi.IN_FORM, description='게시물 제목', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('category', openapi.IN_FORM, description='카테고리', type=openapi.TYPE_STRING,
                              required=False),
            openapi.Parameter('visibility', openapi.IN_FORM, description='공개 범위', type=openapi.TYPE_STRING,
                              enum=['everyone', 'mutual', 'me'], required=False),
            openapi.Parameter('subject', openapi.IN_FORM, description='주제 (네이버 제공 소주제)', type=openapi.TYPE_STRING,
                              enum=[choice[0] for choice in Post.SUBJECT_CHOICES], required=False),
            openapi.Parameter('is_complete', openapi.IN_FORM, description='작성 상태 (true: 작성 완료, false: 임시 저장)',
                              type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('update_texts', openapi.IN_FORM, description='수정할 텍스트 ID 목록 (JSON 형식)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('remove_texts', openapi.IN_FORM, description='삭제할 텍스트 ID 목록 (JSON 형식)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('content', openapi.IN_FORM, description='수정할 텍스트 내용 배열 (JSON 형식)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('font', openapi.IN_FORM, description='글씨체 배열 (JSON 형식)', type=openapi.TYPE_STRING,
                              required=False),
            openapi.Parameter('font_size', openapi.IN_FORM, description='글씨 크기 배열 (JSON 형식)', type=openapi.TYPE_STRING,
                              required=False),
            openapi.Parameter('is_bold', openapi.IN_FORM, description='글씨 굵기 배열 (JSON 형식)', type=openapi.TYPE_STRING,
                              required=False),
            openapi.Parameter('remove_images', openapi.IN_FORM, description='삭제할 이미지 ID 목록 (JSON 형식)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('update_images', openapi.IN_FORM, description='수정할 이미지 ID 목록 (JSON 형식)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('images', openapi.IN_FORM, description='이미지 파일 배열 (새 이미지 업로드)', type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_FILE), required=False),
            openapi.Parameter('captions', openapi.IN_FORM, description='이미지 캡션 배열 (JSON 형식 문자열)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('is_representative', openapi.IN_FORM, description='대표 사진 여부 배열 (JSON 형식 문자열)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('image_group_ids', openapi.IN_FORM, description='이미지가 속한 그룹 배열 (각 이미지마다 개별 입력)',
                              type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), required=False),
            openapi.Parameter('group_captions', openapi.IN_FORM, description='그룹별 이미지 캡션 설정 (ex: {"3": "새 캡션"})',
                              type=openapi.TYPE_OBJECT, required=False),
            openapi.Parameter('group_representative', openapi.IN_FORM, description='대표 이미지 설정 (ex: {"3": true})',
                              type=openapi.TYPE_OBJECT, required=False),
        ],
        responses={200: PostSerializer()},
    )
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()

        # 기본 필드 업데이트
        instance.title = request.data.get('title', instance.title)
        instance.category = request.data.get('category', instance.category)
        instance.visibility = request.data.get('visibility', instance.visibility)
        instance.subject = request.data.get('subject', instance.subject)

        # is_complete 필드 업데이트
        if "is_complete" in request.data:
            new_is_complete = to_boolean(request.data["is_complete"])
            if instance.is_complete and not new_is_complete:
                return Response({"error": "작성 완료된 게시물은 다시 임시 저장 상태로 변경할 수 없습니다."}, status=400)
            instance.is_complete = new_is_complete

        instance.save()

        def parse_json_data(field):
            value = request.data.get(field)
            if isinstance(value, str):
                try:
                    return json.loads(value.replace(" ", "")) if value else []
                except json.JSONDecodeError:
                    return []
            elif isinstance(value, list):
                return value
            elif isinstance(value, int):
                return [value]  # 정수값을 리스트로 변환하여 처리
            return []

        # 텍스트 수정 / 삭제 처리
        update_text_ids = parse_json_data('update_texts')
        remove_text_ids = parse_json_data('remove_texts')
        updated_contents = parse_json_data('content')
        updated_fonts = parse_json_data('font')
        updated_font_sizes = parse_json_data('font_size')
        updated_is_bolds = parse_json_data('is_bold')

        # 기존 텍스트 삭제
        PostText.objects.filter(id__in=remove_text_ids, post=instance).delete()

        # 기존 텍스트 수정
        for idx, text_id in enumerate(update_text_ids):
            try:
                text_obj = PostText.objects.get(id=text_id, post=instance)
                if idx < len(updated_contents): text_obj.content = updated_contents[idx]
                if idx < len(updated_fonts): text_obj.font = updated_fonts[idx]
                if idx < len(updated_font_sizes): text_obj.font_size = updated_font_sizes[idx]
                if idx < len(updated_is_bolds): text_obj.is_bold = updated_is_bolds[idx]
                text_obj.save()
            except PostText.DoesNotExist:
                continue

        # 새 텍스트 추가
        if not remove_text_ids and not update_text_ids:
            for idx in range(len(updated_contents)):
                PostText.objects.create(
                    post=instance,
                    content=updated_contents[idx],
                    font=updated_fonts[idx] if idx < len(updated_fonts) else "nanum_gothic",
                    font_size=updated_font_sizes[idx] if idx < len(updated_font_sizes) else 15,
                    is_bold=updated_is_bolds[idx] if idx < len(updated_is_bolds) else False,
                )

        # ✅ Swagger에서 숫자로 하나씩 추가하는 방식 반영 (post 메서드와 동일하게)
        image_group_ids = request.data.getlist('image_group_ids')  # 리스트로 직접 받음
        if len(image_group_ids) == 1 and isinstance(image_group_ids[0], str) and "," in image_group_ids[0]:
            image_group_ids = image_group_ids[0].split(",")
        image_group_ids = [int(x) for x in image_group_ids] if image_group_ids else []

        # ✅ 이미지 관련 데이터 처리
        images = request.FILES.getlist('images')
        captions = parse_json_data('captions')
        is_representative_flags = parse_json_data('is_representative')
        image_group_ids = parse_json_data('image_group_ids')
        remove_images = parse_json_data('remove_images')
        update_images = parse_json_data('update_images')
        group_captions = parse_json_data('group_captions')
        group_representative = parse_json_data('group_representative')

        PostImage.objects.filter(id__in=remove_images, post=instance).delete()
        for idx, image_id in enumerate(update_images):
            try:
                post_image = PostImage.objects.get(id=image_id, post=instance)
                if idx < len(images):
                    post_image.image.delete()
                    post_image.image = images[idx]
                    post_image.save(update_fields=["image"])
            except PostImage.DoesNotExist:
                continue

        # ✅ image_group_ids가 리스트가 아닐 경우 변환
        image_group_ids = parse_json_data('image_group_ids')
        if not isinstance(image_group_ids, list):
            image_group_ids = [image_group_ids]  # 단일 정수 값이라면 리스트로 변환

        # ✅ group_id 할당 수정 (빈 리스트일 경우 기본값 1)
        created_images = []
        for idx, image in enumerate(images[len(update_images):]):
            group_id = image_group_ids[idx] if image_group_ids and idx < len(image_group_ids) else 1
            caption = captions[idx] if idx < len(captions) else None
            is_representative = is_representative_flags[idx] if idx < len(is_representative_flags) else False

            post_image = PostImage.objects.create(
                post=instance,
                image=image,
                image_group_id=group_id,
                caption=caption,
                is_representative=is_representative
            )
            created_images.append(post_image)

        for group_id, caption in group_captions.items():
            PostImage.objects.filter(post=instance, image_group_id=group_id).update(caption=caption)

        if group_representative:
            selected_group = list(group_representative.keys())[0]
            PostImage.objects.filter(post=instance).update(is_representative=False)
            PostImage.objects.filter(post=instance, image_group_id=selected_group).update(is_representative=True)

        serializer = PostSerializer(instance)
        return Response(serializer.data, status=200)

    @swagger_auto_schema(
        operation_summary="게시물 삭제",
        operation_description="특정 게시물과 관련 이미지를 포함한 모든 데이터를 삭제합니다.",
        responses={204: "삭제 성공"},
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()

        # ✅ 폴더 경로 저장 (main/media/카테고리/제목)
        if instance.images.exists():
            folder_path = os.path.dirname(instance.images.first().image.path)

        # ✅ 관련 이미지 삭제
        for image in instance.images.all():
            if image.image:  # 이미지 파일이 있는 경우
                image.image.storage.delete(image.image.name)  # 물리적 파일 삭제
            image.delete()  # DB 레코드 삭제

        # ✅ 폴더 삭제 (비어 있다면)
        if folder_path and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)  # 폴더 삭제

        if instance.author != request.user:
            return Response({"error": "게시물을 삭제할 권한이 없습니다."}, status=403)

        instance.delete()
        return Response(status=204)

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
        return Post.objects.filter(author=self.request.user, is_complete=False)  # ✅ Boolean 값으로 필터링


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
        return Post.objects.filter(author=self.request.user, is_complete=False)
