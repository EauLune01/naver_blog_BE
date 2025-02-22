from main.serializers.category import CategorySerializer
from rest_framework import generics, status
from rest_framework.generics import ListAPIView,RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from rest_framework.exceptions import NotFound
from django.db.models import Q
from main.models.category import Category
from main.models.profile import Profile
from main.serializers.category import CategorySerializer
from drf_yasg.utils import swagger_auto_schema  # ✅ Swagger 추가
from drf_yasg import openapi  # ✅ Swagger 문서 필드 설정

class CategoryListView(ListAPIView):
    """
    ✅ 특정 사용자가 만든 모든 카테고리 조회 API
    - `urlname`을 입력하면 해당 사용자가 만든 모든 카테고리를 반환 (기본 "게시판" 포함)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer

    def get_queryset(self):
        urlname = self.request.query_params.get("urlname", None)

        if not urlname:
            raise ValidationError("urlname은 필수 입력값입니다.")

        # ✅ urlname을 이용해 Profile 찾고, 연결된 CustomUser 가져오기
        profile = Profile.objects.filter(urlname=urlname).select_related("user").first()
        if not profile:
            raise NotFound("해당 urlname을 가진 사용자가 존재하지 않습니다.")

        user = profile.user  # ✅ Profile과 연결된 CustomUser 가져오기

        # ✅ 특정 사용자가 만든 모든 카테고리 반환 (기본 설정 카테고리 포함)
        return user.categories.all()

    @swagger_auto_schema(
        operation_summary="특정 사용자가 만든 모든 카테고리 조회",
        operation_description="특정 사용자가 만든 모든 카테고리를 조회합니다. (기본 설정 카테고리 포함)",
        manual_parameters=[
            openapi.Parameter(
                'urlname', openapi.IN_QUERY,
                description="조회할 사용자의 URL 이름 (필수)",
                required=True,
                type=openapi.TYPE_STRING
            ),
        ],
        responses={200: CategorySerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class CategoryDetailView(RetrieveAPIView):
    """
    ✅ 특정 사용자가 만든 특정 카테고리 상세 조회 API
    - URL 경로에서 `category_pk`를 받아서 해당 카테고리 정보 조회
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer
    lookup_field = "pk"  # URL에서 `pk`(카테고리 ID)를 조회하는 필드

    def get_object(self):
        urlname = self.request.query_params.get("urlname", None)
        category_pk = self.kwargs.get("pk")

        # ✅ `urlname`이 필수 입력값!
        if not urlname:
            raise ValidationError("urlname은 필수 입력값입니다.")

        # ✅ 특정 사용자의 프로필 가져오기
        profile = Profile.objects.filter(urlname=urlname).select_related("user").first()
        if not profile:
            raise NotFound("해당 urlname을 가진 사용자가 존재하지 않습니다.")

        user = profile.user  # ✅ Profile과 연결된 CustomUser 가져오기

        # ✅ 특정 사용자가 만든 특정 카테고리 가져오기
        category = user.categories.filter(pk=category_pk).first()
        if not category:
            raise NotFound("해당 사용자의 해당 카테고리는 존재하지 않습니다.")

        return category

    @swagger_auto_schema(
        operation_summary="특정 사용자가 만든 특정 카테고리 상세 조회",
        operation_description="특정 사용자가 만든 특정 카테고리 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                'urlname', openapi.IN_QUERY,
                description="조회할 사용자의 URL 이름 (필수)",
                required=True,
                type=openapi.TYPE_STRING
            ),
        ],
        responses={200: CategorySerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MyCategoryListView(generics.ListCreateAPIView):
    """
    ✅ 내 카테고리만 조회 (GET /category/)
    ✅ 새로운 카테고리 추가 (POST /category/)
    """
    permission_classes = [IsAuthenticated]  # ✅ 로그인한 사용자만 접근 가능
    serializer_class = CategorySerializer

    def get_queryset(self):
        """ 🔹 현재 로그인한 사용자의 카테고리만 조회 """
        return Category.objects.filter(user=self.request.user)  # ✅ ManyToManyField 사용하지 않음

    @swagger_auto_schema(
        operation_summary="내 카테고리 조회",
        operation_description="현재 로그인한 사용자의 카테고리만 조회합니다.",
        responses={200: CategorySerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="내 계정에 새로운 카테고리 추가하기",
        operation_description="새로운 카테고리를 추가하고 현재 로그인한 유저의 카테고리에 추가합니다. (최대 30글자 제한)",
        request_body=CategorySerializer,
        responses={
            201: CategorySerializer,
            400: "잘못된 요청 (30글자 초과 시 오류)"
        }
    )
    def create(self, request, *args, **kwargs):
        """ ✅ 새로운 카테고리 추가 (30글자 제한) """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            category = Category.objects.create(user=request.user, name=serializer.validated_data["name"])  # ✅ ForeignKey로 생성
            return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    ✅ 내 특정 카테고리 조회 (GET /categories/<id>/)
    ✅ 내 특정 카테고리 수정 (PATCH /categories/<id>/)
    ✅ 내 특정 카테고리 삭제 (DELETE /categories/<id>/, 단 '게시판' 삭제 불가)
    """
    permission_classes = [IsAuthenticated]  # ✅ 로그인한 사용자만 접근 가능
    serializer_class = CategorySerializer

    def get_queryset(self):
        """ 🔹 현재 로그인한 사용자의 카테고리만 조회 """
        return Category.objects.filter(user=self.request.user)  # ✅ ManyToManyField 제거

    @swagger_auto_schema(
        operation_summary="내 특정 카테고리 조회",
        operation_description="카테고리 ID를 입력하면 해당 카테고리를 조회합니다.",
        responses={200: CategorySerializer, 404: "카테고리를 찾을 수 없습니다."}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="내 특정 카테고리 수정 (PUT 사용 금지)",
        operation_description="카테고리명을 수정합니다. (최대 30글자 제한) \n\n **PUT 요청은 허용되지 않습니다.**",
        request_body=CategorySerializer,
        responses={
            200: CategorySerializer,
            400: "잘못된 요청 (30글자 초과 시 오류)"
        }
    )
    def patch(self, request, *args, **kwargs):
        """ ✅ 내 카테고리 수정 (30글자 제한) """
        partial = kwargs.pop('partial', True)  # ✅ PUT을 막고 PATCH만 허용
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        auto_schema=None  # ✅ Swagger에서 PUT을 숨김
    )
    def put(self, request, *args, **kwargs):
        """ ❌ PUT 요청 비활성화 (Swagger 문서에서도 안 보이게 설정) """
        return Response({"error": "PUT 요청은 허용되지 않습니다. PATCH 요청을 사용하세요."},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @swagger_auto_schema(
        operation_summary="내 특정 카테고리 삭제",
        operation_description="카테고리를 삭제합니다. 단, '게시판' 카테고리는 삭제할 수 없습니다.",
        responses={204: "카테고리가 삭제되었습니다.", 403: "⚠️ '게시판' 카테고리는 삭제할 수 없습니다."}
    )
    def delete(self, request, *args, **kwargs):
        """ ✅ 내 특정 카테고리 삭제 (단, '게시판' 삭제 불가) """
        instance = self.get_object()
        if instance.name == "게시판":
            return Response({"error": "⚠️ '게시판' 카테고리는 삭제할 수 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        self.perform_destroy(instance)
        return Response({"message": "카테고리가 삭제되었습니다."}, status=status.HTTP_204_NO_CONTENT)
