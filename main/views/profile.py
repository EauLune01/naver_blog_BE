from django.db import models
from django.conf import settings
from rest_framework.generics import RetrieveUpdateDestroyAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from ..models.profile import Profile
from main.models.neighbor import Neighbor
from ..serializers.profile import ProfileSerializer,UrlnameUpdateSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError


class ProfileDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # ✅ 파일 업로드 지원

    def get_object(self):
        """ ✅ 현재 로그인된 사용자의 프로필 반환 """
        return Profile.objects.get(user=self.request.user)

    def remove_urlname_from_request(self, request):
        """ ✅ `PUT`, `PATCH` 요청 시 `urlname` 자동 제거 """
        mutable_data = request.data.copy()
        mutable_data.pop("urlname", None)  # `urlname`이 있으면 삭제
        return mutable_data

    @swagger_auto_schema(
        operation_summary="현재 사용자 프로필 조회",
        operation_description="현재 로그인된 사용자의 프로필 정보를 반환합니다.",
        responses={200: openapi.Response(description="성공적으로 프로필 반환", schema=ProfileSerializer())}
    )
    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data, status=200)

    @swagger_auto_schema(
        operation_summary="현재 사용자 프로필 전체 수정",
        operation_description="현재 로그인된 사용자의 프로필 정보를 전체 수정합니다.",
        manual_parameters=[  # ✅ Swagger에 반영할 필드 (urlname 제외)
            openapi.Parameter('blog_name', openapi.IN_FORM, description='블로그 이름', type=openapi.TYPE_STRING),
            openapi.Parameter('blog_pic', openapi.IN_FORM, description='블로그 사진', type=openapi.TYPE_FILE),
            openapi.Parameter('username', openapi.IN_FORM, description='사용자 이름', type=openapi.TYPE_STRING),
            openapi.Parameter('user_pic', openapi.IN_FORM, description='프로필 사진', type=openapi.TYPE_FILE),
            openapi.Parameter('intro', openapi.IN_FORM, description='자기소개', type=openapi.TYPE_STRING),
            openapi.Parameter('neighbor_visibility', openapi.IN_FORM, description="서로이웃 목록 공개 여부", type=openapi.TYPE_BOOLEAN),
        ],
        responses={200: openapi.Response(description="성공적으로 프로필 전체 수정", schema=ProfileSerializer())}
    )
    def put(self, request, *args, **kwargs):
        request_data = self.remove_urlname_from_request(request)  # ✅ `urlname` 자동 제거
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=200)

    @swagger_auto_schema(
        operation_summary="현재 사용자 프로필 부분 수정",
        operation_description="현재 로그인된 사용자의 프로필을 부분 수정합니다.",
        manual_parameters=[  # ✅ Swagger에 반영할 필드 (urlname 제외)
            openapi.Parameter('blog_name', openapi.IN_FORM, description='블로그 이름', type=openapi.TYPE_STRING),
            openapi.Parameter('blog_pic', openapi.IN_FORM, description='블로그 사진', type=openapi.TYPE_FILE),
            openapi.Parameter('username', openapi.IN_FORM, description='사용자 이름', type=openapi.TYPE_STRING),
            openapi.Parameter('user_pic', openapi.IN_FORM, description='프로필 사진', type=openapi.TYPE_FILE),
            openapi.Parameter('intro', openapi.IN_FORM, description='자기소개', type=openapi.TYPE_STRING),
        ],
        responses={200: openapi.Response(description="성공적으로 프로필 수정", schema=ProfileSerializer())}
    )
    def patch(self, request, *args, **kwargs):
        request_data = self.remove_urlname_from_request(request)  # ✅ `urlname` 자동 제거
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=200)


from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.generics import UpdateAPIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from main.serializers.profile import UrlnameUpdateSerializer
from main.models.profile import Profile

from rest_framework.exceptions import ValidationError

class ProfileUrlnameUpdateView(UpdateAPIView):
    """
    ✅ `urlname`만 변경하는 API (PATCH /api/profile/urlname/)
    ✅ `urlname`은 한 번만 변경 가능 (urlname_edit_count >= 1이면 변경 불가)
    """
    serializer_class = UrlnameUpdateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # ✅ `FormData` 방식 지원

    @swagger_auto_schema(
        operation_summary="URL 이름 변경 (한 번만 가능)",
        operation_description="현재 로그인된 사용자의 URL 이름(urlname)을 변경합니다. "
                              "urlname은 한 번만 변경할 수 있습니다. "
                              "이미 변경한 경우 다시 변경할 수 없습니다.",
        manual_parameters=[
            openapi.Parameter(
                'urlname', openapi.IN_FORM, description='새로운 URL 이름', type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                description="URL 이름 변경 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="응답 메시지"),
                        "urlname": openapi.Schema(type=openapi.TYPE_STRING, description="변경된 URL 이름"),
                    }
                )
            ),
            400: openapi.Response(description="변경 불가능 (한 번만 변경 가능)"),
            405: openapi.Response(description="PUT 요청은 지원되지 않습니다."),
        }
    )
    def patch(self, request, *args, **kwargs):
        profile = Profile.objects.get(user=request.user)

        # ✅ URL 이름은 한 번만 변경 가능하도록 검증
        if profile.urlname_edit_count >= 1:
            raise ValidationError({"error": "URL 이름은 한 번만 변경할 수 있습니다."})

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # ✅ `urlname` 변경
        profile.urlname = serializer.validated_data["urlname"]
        profile.urlname_edit_count += 1  # ✅ 변경 횟수 증가
        profile.save()

        return Response({"message": "URL 이름이 변경되었습니다.", "urlname": profile.urlname}, status=200)

    def put(self, request, *args, **kwargs):
        """ ✅ `PUT` 요청을 명확하게 차단 """
        return Response({"error": "PUT 요청은 지원되지 않습니다. PATCH 요청을 사용하세요."}, status=405)



class ProfilePublicView(RetrieveAPIView):
    """
    ✅ 타인의 프로필 조회 (GET /api/profile/{urlname}/)
    - 프로필이 존재하지 않으면 404 반환.
    - 로그인하지 않은 사용자도 조회 가능.
    - 서로이웃 여부(`is_neighbor`)를 추가하여 반환.
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # 로그인하지 않아도 조회 가능

    @swagger_auto_schema(
        operation_summary="타인의 프로필 조회",
        operation_description="특정 사용자의 블로그 프로필을 조회합니다. 현재 로그인한 사용자가 조회 대상과 서로이웃인지 여부(`is_neighbor`)를 함께 반환합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="urlname",
                in_=openapi.IN_PATH,
                description="조회할 사용자의 URL 이름",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="성공적으로 프로필을 반환",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "urlname": openapi.Schema(type=openapi.TYPE_STRING, description="사용자의 URL 이름"),
                        "blog_name": openapi.Schema(type=openapi.TYPE_STRING, description="블로그 이름"),
                        "blog_pic": openapi.Schema(type=openapi.TYPE_STRING, format="url", description="블로그 프로필 이미지 URL"),
                        "username": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이름"),
                        "user_pic": openapi.Schema(type=openapi.TYPE_STRING, format="url", description="프로필 사진 URL"),
                        "intro": openapi.Schema(type=openapi.TYPE_STRING, description="사용자의 자기소개"),
                        "is_neighbor": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="현재 로그인한 사용자가 조회 대상과 서로이웃인지 여부")
                    }
                )
            ),
            404: openapi.Response(description="해당 사용자의 프로필을 찾을 수 없음")
        }
    )
    def get(self, request, urlname):
        profile = get_object_or_404(Profile, urlname=urlname)
        serializer = self.get_serializer(profile)

        # ✅ 현재 로그인한 사용자가 서로이웃인지 확인 (status="accepted"인 경우만 체크)
        is_neighbor = False
        if request.user.is_authenticated:
            is_neighbor = Neighbor.objects.filter(
                (Q(from_user=request.user, to_user=profile.user) |
                 Q(from_user=profile.user, to_user=request.user)),
                status="accepted"
            ).exists()

        response_data = serializer.data
        response_data["is_neighbor"] = is_neighbor  # ✅ 서로이웃 여부 추가

        return Response(response_data)








