from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..models import Post, PostImage,CustomUser,Profile
from ..models.neighbor import Neighbor
from django.db.models import Q
from ..serializers import PostSerializer
import json
import os
import shutil
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import now, timedelta
from pickle import FALSE
from main.utils import *

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
        category_name = self.request.query_params.get('category_name', None)
        pk = self.request.query_params.get('pk', None)
        keyword = self.request.query_params.get('keyword', None)

        # ✅ category_name만 존재할 경우 에러 처리
        if category_name and not (urlname or pk):
            raise ValidationError("카테고리만 입력된 경우는 허용하지 않습니다.")

        # ✅ keyword는 단독으로 사용해야 함
        if keyword and (urlname or category_name or pk):
            raise ValidationError("keyword는 단독으로 사용해야 합니다.")

        request_user = self.request.user  # ✅ API 요청을 보낸 유저 (예: sm)
        profile_user = None  # ✅ urlname을 통한 조회 유저 (예: kdy)

        # ✅ `urlname`이 주어진 경우, Profile에서 해당 `urlname`을 가진 유저 찾기
        if urlname:
            profile = Profile.objects.filter(urlname=urlname).select_related("user").first()
            if not profile:
                return Post.objects.none()  # 존재하지 않는 경우 빈 쿼리셋 반환
            profile_user = profile.user  # ✅ Profile의 `user`를 사용
        else:
            profile_user = request_user  # ✅ urlname이 없으면 기본적으로 API 요청한 유저 사용

        # ✅ keyword가 주어진 경우, 해당 키워드의 게시물만 필터링
        if keyword:
            if keyword not in dict(Post.KEYWORD_CHOICES):
                raise ValidationError(f"'{keyword}'은(는) 유효하지 않은 keyword 값입니다.")
            queryset = Post.objects.filter(keyword=keyword, status="published", user=profile_user)
            return queryset

        # ✅ `profile_user`가 작성한 모든 `published` 게시물 가져오기
        queryset = Post.objects.filter(user=profile_user, status="published")

        # ✅ `category_name`을 이용해 ForeignKey `category` 필터링
        if category_name:
            try:
                category = Category.objects.get(name=category_name)  # 🔹 문자열로 받은 이름을 Category 모델에서 조회
                queryset = queryset.filter(category=category)
            except Category.DoesNotExist:
                return Post.objects.none()  # 존재하지 않는 카테고리일 경우 빈 쿼리셋 반환

        # ✅ 특정 `pk`의 게시물 조회
        if pk:
            queryset = queryset.filter(pk=pk)
        return queryset

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
        post_status = request.data.get('status', 'draft')# ✅ Post 모델의 status 사용
        visibility = request.data.get('visibility', 'everyone')  # ✅ visibility 추가
        created_at = request.data.get('created_at')  # ✅ created_at 추가

        if not title:
            return Response({"error": "제목은 필수 항목입니다."}, status=400)

        if category_name:
            try:
                category = user.categories.get(name=category_name)  # ✅ 변경된 부분
            except Category.DoesNotExist:
                return Response({"error": f"'{category_name}'은(는) 유효하지 않은 카테고리입니다."}, status=400)
        else:
            category = user.categories.first()  # ✅ 변경된 부분

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

        # 이미지 저장 saveimageutil 함수를 불러와서 적용한다.
        # 작업 내용 : 다중 이미지 저장, 캡션, 대표사진 여부 저장, BASE64 인코딩 후 url 변경
        save_images_from_request(post, request)

        serializer = PostSerializer(post)

        if post_status == 'published':
            return Response({"message": "게시물이 성공적으로 생성되었습니다.", "post": serializer.data}, status=201)
        elif post_status == 'draft':
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
    ✅ 로그인한 사용자가 작성한 게시물 중 가장 최근 `published` 상태인 게시물 조회 API
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_object(self):
        user = self.request.user

        # 현재 로그인한 사용자의 `published` 상태인 게시물 중 가장 최신(created_at 기준) 1개 가져오기
        post = Post.objects.filter(user=user, status='published').order_by('-created_at').first()

        if not post:
            raise NotFound("출판된 게시물이 없습니다.")

        return post

    @swagger_auto_schema(
        operation_summary="내가 작성한 가장 최근 게시물 조회",
        operation_description="로그인한 사용자가 작성한 게시물 중 `published` 상태이며, 가장 최근 생성된 게시물 1개를 조회합니다.",
        responses={200: PostSerializer()},
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PostMutualView(ListAPIView):
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

        return queryset

    @swagger_auto_schema(
        operation_summary="서로이웃 게시물 목록 조회",
        operation_description="최근 1주일 내 작성된 서로이웃 공개 게시물을 조회합니다.",
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
            openapi.Parameter('is_complete', openapi.IN_FORM,
                              description='작성 상태 (true: 작성 완료, false: 임시 저장 → 변경 가능, 단 true → false 변경 불가)',
                              type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('update_texts', openapi.IN_FORM, description='수정할 텍스트 ID 목록 (JSON 형식)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('remove_texts', openapi.IN_FORM, description='삭제할 텍스트 ID 목록 (JSON 형식)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('content', openapi.IN_FORM, description='수정할 텍스트 내용 배열 (JSON 형식)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('font', openapi.IN_FORM, description='글씨체 배열 (JSON 형식)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('font_size', openapi.IN_FORM, description='글씨 크기 배열 (JSON 형식)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('is_bold', openapi.IN_FORM, description='글씨 굵기 배열 (JSON 형식)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('remove_images', openapi.IN_FORM, description='삭제할 이미지 ID 목록 (JSON 형식 문자열)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('update_images', openapi.IN_FORM, description='수정할 이미지 ID 목록 (JSON 형식 문자열)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('images', openapi.IN_FORM, description='이미지 파일 배열 (새 이미지 업로드)', type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_FILE), required=False),
            openapi.Parameter('captions', openapi.IN_FORM, description='이미지 캡션 배열 (JSON 형식 문자열)',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('is_representative', openapi.IN_FORM, description='대표 사진 여부 배열 (JSON 형식 문자열)',
                              type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: PostSerializer()},
    )
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()

        # ✅ subject 값 검증은 serializer에서 처리되므로 별도 검증 X
        instance.subject = request.data.get('subject', instance.subject)

        # ✅ `is_complete=True`인 게시물은 `False`로 변경할 수 없음
        if "is_complete" in request.data:
            new_is_complete = request.data["is_complete"] in [True, "true", "True", 1, "1"]
            if instance.is_complete and not new_is_complete:
                return Response({"error": "작성 완료된 게시물은 다시 임시 저장 상태로 변경할 수 없습니다."}, status=400)
            instance.is_complete = new_is_complete  # ✅ Boolean 값 저장

        # ✅ visibility 검증도 serializer에서 자동으로 처리됨 → 별도 검증 삭제
        instance.visibility = request.data.get('visibility', instance.visibility)

        # ✅ 기본 필드 업데이트
        instance.title = request.data.get('title', instance.title)
        instance.category = request.data.get('category', instance.category)
        instance.save()

        # ✅ JSON 데이터 파싱 함수 (모든 JSON 필드를 안전하게 처리)
        def parse_json_data(field):
            try:
                if isinstance(request.data, list):  # 🔥 리스트 자체가 들어왔을 때
                    return request.data
                elif isinstance(request.data.get(field), str):  # 기존 방식 (필드가 JSON 문자열일 때)
                    return json.loads(request.data.get(field, "[]"))
                elif isinstance(request.data.get(field), list):  # `field` 필드가 리스트일 때
                    return request.data.get(field, [])
                return []
            except json.JSONDecodeError:
                return []

        # ✅ 텍스트 수정 / 삭제
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

                if idx < len(updated_contents):
                    text_obj.content = updated_contents[idx]
                if idx < len(updated_fonts):
                    text_obj.font = updated_fonts[idx]
                if idx < len(updated_font_sizes):
                    text_obj.font_size = updated_font_sizes[idx]
                if idx < len(updated_is_bolds):
                    text_obj.is_bold = updated_is_bolds[idx]

                text_obj.save()
            except PostText.DoesNotExist:
                continue
        # ✅ 새 텍스트 추가 (remove_texts와 update_texts가 비어있다면)
        if not remove_text_ids and not update_text_ids:
            for idx in range(len(updated_contents)):
                PostText.objects.create(
                    post=instance,
                    content=updated_contents[idx],  # 필수
                    font=updated_fonts[idx] if idx < len(updated_fonts) else "nanum_gothic",  # 기본값: 나눔고딕
                    font_size=updated_font_sizes[idx] if idx < len(updated_font_sizes) else 15,  # 기본값: 15
                    is_bold=updated_is_bolds[idx] if idx < len(updated_is_bolds) else False,  # 기본값: False
                )

        # ✅ 이미지 관련 데이터 가져오기
        images = request.FILES.getlist('images')  # 새로 업로드된 이미지 파일 리스트
        captions = parse_json_data('captions')  # 캡션 배열 (id 없음)
        is_representative_flags = parse_json_data('is_representative')  # 대표 여부 배열 (id 없음)
        remove_images = parse_json_data('remove_images')  # 삭제할 이미지 ID 배열
        update_images = parse_json_data('update_images')  # 기존 이미지 ID 리스트

        # ✅ 기존 이미지 삭제
        PostImage.objects.filter(id__in=remove_images, post=instance).delete()

        # ✅ 기존 이미지 수정 (ID 유지) - 업로드된 파일과 ID 매칭
        for idx, image_id in enumerate(update_images):
            try:
                post_image = PostImage.objects.get(id=image_id, post=instance)

                # ✅ 새로 업로드된 이미지가 있다면 교체
                if idx < len(images):
                    post_image.image.delete()  # 기존 이미지 삭제
                    post_image.image = images[idx]  # 새로운 이미지 저장

                # ✅ captions 리스트의 idx가 유효하다면 업데이트
                if idx < len(captions):
                    post_image.caption = captions[idx]

                # ✅ is_representative 값도 업데이트
                if idx < len(is_representative_flags):
                    post_image.is_representative = is_representative_flags[idx]

                post_image.save()
            except PostImage.DoesNotExist:
                continue  # 존재하지 않으면 무시

        # ✅ 새 이미지 추가 (ID가 새로 생성됨)
        for idx, image in enumerate(images[len(update_images):]):  # 기존 이미지 수정 후 남은 파일들
            PostImage.objects.create(
                post=instance,
                image=image,
                caption=captions[idx] if idx < len(captions) else None,
                is_representative=is_representative_flags[idx] if idx < len(is_representative_flags) else False,
            )

        # ✅ 대표 이미지 중복 검사 및 자동 설정
        representative_images = instance.images.filter(is_representative=True)
        if representative_images.count() > 1:
            return Response({"error": "대표 이미지는 한 개만 설정할 수 있습니다."}, status=400)

        if representative_images.count() == 0 and instance.images.exists():
            first_image = instance.images.first()
            first_image.is_representative = True
            first_image.save()

        # ✅ 응답 반환
        serializer = PostSerializer(instance)
        return Response(serializer.data, status=200)

    @swagger_auto_schema(
        operation_summary="게시물 삭제",
        operation_description="특정 게시물과 관련 이미지를 포함한 모든 데이터를 삭제합니다.",
        responses={204: "삭제 성공"},
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        folder_path = None

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